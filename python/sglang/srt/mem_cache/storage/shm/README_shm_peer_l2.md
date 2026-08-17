# HiCache `shm_peer_l2` — Cross-DP Peer L2 Cache

## 1. Bài toán

Khi chạy SGLang với Data Parallelism (`--dp N`), mỗi DP rank phục vụ một tập request độc lập.
Với model lớn (DeepSeek, GLM-5.2…), prefix compute rất tốn kém: một đoạn system prompt dài
2000 token có thể mất vài giây prefill. KV cache của prefix đó được lưu vào HiCache L2 (host RAM)
của rank đó.

**Vấn đề: L2 của mỗi rank là private — rank kia không thấy, phải recompute từ đầu.**

```
Không có shm_peer_l2:

  Request A → Rank 0                Request B → Rank 1  (cùng system prompt)
  ──────────────────────────         ──────────────────────────
  GPU: compute prefix (3 s)          GPU: compute prefix (3 s)  ← lãng phí
  L2 buffer Rank 0: [KV slot 42]     L2 buffer Rank 1: [KV slot 7]  ← private
```

Kết quả: cùng một prefix được recompute lại mỗi lần nó rơi vào rank khác. Với long-context
hoặc shared system prompt (RAG, agent loop), đây là bottleneck nghiêm trọng.

---

## 2. Giải pháp

`shm_peer_l2` cho phép các DP rank **chia sẻ L2 KV cache** qua shared memory mà không
cần copy thêm. Cơ chế gồm hai phần:

1. **Shared L2 buffer** — tất cả rank map cùng physical SHM pages thay vì mỗi rank có buffer riêng.
2. **Peer index** — một hash table nhỏ trong SHM ghi lại `key → (dp_rank, slot_start)`,
   cho phép rank B tìm và đọc trực tiếp slot của rank A.

```
Dùng shm_peer_l2:

  Request A → Rank 0                Request B → Rank 1  (cùng system prompt)
  ──────────────────────────         ──────────────────────────
  GPU: compute prefix (3 s)          index lookup → HIT: Rank 0, slot 42
  Shared L2: ghi slot 42             memcpy(slot_42 → own_slot)  (< 1 ms)
  Index: ghi (key → rank=0, slot=42) GPU DMA: own_slot → GPU    (< 10 ms)
                                      SKIP compute ✓
```

**Rank B chỉ tốn: 1 index lookup + 1 memcpy trong SHM + 1 DMA. Không recompute.**

### So sánh với `shm_cross_dp`

| | `shm_cross_dp` | `shm_peer_l2` |
|---|---|---|
| L2 buffer | Shared physical pages | Shared physical pages |
| "L3" data store | SHM file chứa full page copy (ghi thêm 1 lần) | Không có |
| Write path | GPU → L2 → copy vào SHM L3 file | GPU → shared L2 → ghi 288B pointer vào index |
| Read path | SHM L3 → CPU buf → L2 → GPU | memcpy trong SHM (zero-copy) → GPU |
| Overhead memory | shared L2 + toàn bộ data duplicate | shared L2 + index ~vài chục MB |
| Interface | V0 (`batch_set` / `batch_get`) | V1 (`batch_set_v1` / `batch_get_v1`) |

`shm_peer_l2` không cần khai báo `shm_cross_dp` riêng — tự thiết lập shared allocator.

---

## 3. Cơ chế chi tiết

### 3.1 Shared memory files

```
/dev/shm/
├── sglang_l2_<model_slug>_pp<r>_<s>.mmap        # L2 data buffer (shared vật lý, hàng trăm GB)
├── sglang_l2_idx_<model_slug>_pp<r>_<s>.bin      # Index hash table (288 B/entry, vài chục MB)
└── sglang_l2_gen_<model_slug>_pp<r>_<s>.bin      # Generation counter array (4 B/page)
```

### 3.2 Layout index SHM

```
[256-byte header]
  magic:    uint64  0xCAFEFEED0002   ← v2 (thêm generation field so với v1)
  capacity: uint64  số slot trong hash table
  ready:    uint8   1 khi init xong

[capacity × 288-byte entries]  ← direct-mapped hash table
  Offset  0    valid:    uint8    0=empty, 1=valid (visibility fence)
  Offset  1    dp_rank:  uint8    rank nào sở hữu slot này
  Offset  2    gen:      uint32   generation tại thời điểm write
  Offset  8    slot_idx: uint64   first token index trong L2 pool
  Offset 16    hash64:   uint64   SHA-256(key)[:8] để verify
  Offset 24    key_len:  uint16
  Offset 32    key_str:  uint8[256]
```

### 3.3 Generation counter SHM

```
uint32[page_num]
```

Mỗi page trong L2 pool có một counter riêng. Counter tăng khi page đó được
**cấp phát lại** (evict page cũ, dùng cho token mới). Dùng để phát hiện stale index entry
(xem 3.5).

### 3.4 Write path (`batch_set_v1`)

Sau khi backup thread ghi xong KV pages lên shared L2 buffer:

```python
# Với mỗi key:
bucket = hash64(key) % capacity          # direct-map, không có chaining
entry.valid = 0                          # invalidate trước (readers bỏ qua)
entry.dp_rank  = self._dp_rank
entry.gen      = gen_arr[slot_start // page_size]  # snapshot generation
entry.slot_idx = slot_start
entry.hash64   = hash64(key)
entry.key_str  = key
entry.valid = 1                          # publish: readers giờ mới thấy
```

Lock: `threading.Lock` (in-process) + `fcntl.LOCK_EX` (cross-process).

### 3.5 Read path (`batch_get_v1`)

**Phase 1 — Index lookup** (giữ `LOCK_SH`):

```python
bucket = hash64(key) % capacity
if entry.valid and entry.hash64 == h and entry.key == key:
    if entry.dp_rank == self._dp_rank:
        → SKIP  # không đọc từ chính mình
    stored_gen  = entry.gen
    current_gen = gen_arr[entry.slot_idx // page_size]
    if stored_gen != current_gen:
        → MISS  # slot đã bị reuse → stale, bỏ qua
    peer_slot = entry.slot_idx  # HIT
```

**Phase 2 — Data copy** (không cần lock):

```python
page_data = pool.get_data_page(peer_slot)   # đọc từ slot của rank kia
pool.set_from_flat_data_page(own_slot, page_data)  # ghi vào slot của mình
```

### 3.6 Stale-read prevention

```
Timeline:
  t=0: Rank A ghi slot 42, gen_arr[page=1]=5 → index entry: {slot=42, gen=5}
  t=1: Rank A evict slot 42, alloc lại cho token khác
       → _alloc_callback() → gen_arr[page=1]++ = 6
  t=2: Rank B lookup → thấy entry {slot=42, gen=5}
       → đọc gen_arr[page=1] = 6
       → 5 ≠ 6 → MISS  ✓  (không copy dữ liệu sai)
```

`_alloc_callback` được đăng ký tại `register_mem_pool_host` và được gọi bởi
`HostKVCache.alloc()` ngay trước khi trả về indices mới — tức là counter tăng
**trước** khi data cũ bị overwrite, đảm bảo Rank B không bao giờ đọc data từ
"người thuê mới".

### 3.7 Collision handling

Hash table là direct-mapped (không có chaining, không có probing). Nếu hai key
hash vào cùng bucket, entry mới **ghi đè** entry cũ. Entry cũ vẫn còn trong L2
nhưng không còn trong index → chỉ mất khả năng tìm thấy qua peer, không mất data.

Capacity mặc định = `page_num × 4` (load factor 25%) để giữ collision rate thấp.
Server log collision rate mỗi 10,000 writes; warning khi > 10%.

---

## 4. Luồng hoạt động end-to-end

### Request 1 → Rank 0 (cache miss, phải compute)

```
Rank 0: match_prefix() → L1 MISS
      → prefetch_from_storage() → index MISS (chưa có gì)
      → GPU compute prefix tokens
      → write_backup(): GPU → CPU DMA → shared L2 SHM [slot 42]
      → backup_thread: batch_set_v1()
          → _write_entry(key, dp_rank=0, slot_start=42, gen=current)
```

### Request 2 → Rank 1 (cùng prefix, đọc từ Rank 0)

```
Rank 1: match_prefix() → L1 MISS
      → prefetch_from_storage() → batch_get_v1()
          Phase 1 (LOCK_SH):
            index lookup → dp_rank=0 ≠ self=1 → HIT
            check gen: stored==current → data valid
            peer_slot = 42
          Phase 2 (no lock):
            memcpy(shared_L2[42] → shared_L2[own_slot])
      → GPU DMA: own_slot → L1 GPU Rank 1
      → SKIP compute  ✓
```

---

## 5. Điều kiện tiên quyết

- `--dp-size >= 2`
- Tất cả DP rank chạy trên **cùng node** — `/dev/shm` là tmpfs node-local
- `--hicache-write-policy write_through` — bắt buộc; `write_back` chỉ flush khi evict khỏi L1, Rank B sẽ không thấy data kịp thời
- `/dev/shm` đủ dung lượng (xem mục 7)

---

## 6. Cấu hình

### Launch command

```bash
python -m sglang.launch_server \
    --model-path <model> \
    --tp-size <tp> \
    --dp-size 2 \
    --hicache-size <L2_GB> \
    --hicache-write-policy write_through \
    --hicache-io-backend direct \
    --hicache-mem-layout page_first_direct \
    --hicache-storage-backend shm_peer_l2
```

### Tuỳ chỉnh capacity và thư mục SHM

```bash
    --hicache-storage-backend-extra-config '{"peer_l2_capacity": 262144, "peer_l2_shm_dir": "/dev/shm"}'
```

Nếu bỏ qua `peer_l2_capacity`, server tự tính theo `page_num × 4` và ghi log tại startup.

### Config trong docker compose (GLM-5.2, 4× H200)

```yaml
worker:
  shm_size: 32g        # /dev/shm chia sẻ giữa các DP rank trong cùng container
  ipc: host            # bắt buộc: share /dev/shm với host và container khác
  command: >
    python3 -m sglang.launch_server
    --dp 4
    --hicache-size 64
    --hicache-write-policy write_through
    --hicache-io-backend direct
    --hicache-mem-layout page_first_direct
    --hicache-storage-backend shm_peer_l2
```

---

## 7. Tính `peer_l2_capacity` và dung lượng `/dev/shm`

```python
def calc_peer_l2_capacity(
    hicache_size_gb: float,
    page_size_tokens: int = 32,
    num_layers: int = 80,
    num_kv_heads: int = 8,   # GQA heads
    head_dim: int = 128,
    dtype_bytes: int = 2,    # bf16=2, fp8=1
    load_factor_inv: int = 4,
):
    size_per_token  = head_dim * num_kv_heads * num_layers * dtype_bytes * 2  # K+V
    page_size_bytes = size_per_token * page_size_tokens
    page_num        = int(hicache_size_gb * 1e9 / page_size_bytes)
    capacity        = page_num * load_factor_inv
    index_mb        = capacity * 288 / 1024**2
    gen_mb          = page_num * 4 / 1024**2
    print(f"page_size       : {page_size_bytes / 1024**2:.2f} MB")
    print(f"page_num        : {page_num:,}")
    print(f"capacity        : {capacity:,}")
    print(f"index file      : {index_mb:.1f} MB")
    print(f"gen array       : {gen_mb:.2f} MB")
    print(f"/dev/shm usage  : L2_buffer + {index_mb + gen_mb:.1f} MB overhead")
```

Ví dụ — Llama 70B (GQA 8 heads), bf16, L2=475 GB:

```
page_size       : 10.00 MB
page_num        : 47,683
capacity        : 190,732  (round up → 262,144 = 2^18)
index file      : 54.8 MB
gen array       : 0.18 MB
/dev/shm usage  : 475 GB + ~55 MB overhead
```

**`load_factor_inv`:**

| Giá trị | Load factor | Khi nào dùng |
|---|---|---|
| 2 | 50% | RAM tight |
| 4 | 25% | Recommended (mặc định) |
| 8 | 12.5% | Prefix rất dài, cần hit rate tối đa |

---

## 8. Verify hoạt động

```bash
# 1. Kiểm tra SHM files sau startup
ls -lh /dev/shm/sglang_l2*
# Kỳ vọng: 1 file .mmap lớn (~L2 size) + 4 file nhỏ (.bin × 2, .bin.lock × 2)

# 2. Log startup — Rank 0 tạo, Rank 1+ attach
grep "HiCacheShmPeerL2" /path/to/sglang.log
# Rank 0: "HiCacheShmPeerL2: created index .../sglang_l2_idx_...  capacity=262144"
# Rank 1: "HiCacheShmPeerL2: attached to existing index ..."

# 3. Auto-computed capacity
grep "auto-computed peer_l2_capacity" /path/to/sglang.log

# 4. Collision rate (log mỗi 10,000 writes; warning nếu > 10%)
grep "collision rate" /path/to/sglang.log

# 5. Dung lượng /dev/shm
df -h /dev/shm
```

---

## 9. Những điểm cần chú ý

**1. `write_through` bắt buộc**
`write_back` chỉ flush L2 khi evict khỏi L1. Rank B sẽ miss index cho đến khi
eviction xảy ra — có thể hàng phút sau. Luôn dùng `write_through` với `shm_peer_l2`.

**2. Rank B phải đợi Rank A flush**
Nếu Rank A chưa chạy xong `backup_thread`, Rank B sẽ miss index và compute lại.
Đây là behavior đúng — cache best-effort, không có coordination. Với `write_through`,
khoảng trễ này rất nhỏ (< 1 request roundtrip).

**3. Chỉ hoạt động trong cùng node**
`/dev/shm` là tmpfs node-local. Nếu DP rank nằm trên node khác, dùng `mooncake` hoặc `nixl`.

**4. Stale SHM file sau restart**
Files SHM tồn tại sau khi stop server. SGLang tự detect stale (kiểm tra magic + capacity +
file size) và recreate khi start. Để giải phóng ngay:

```bash
rm -f /dev/shm/sglang_l2*
```

**5. Sidecar pools không được replicate**
`shm_peer_l2` chỉ hỗ trợ main KV pool qua V1 interface. Sidecar pools (DSA, Mamba…)
trả về all-False — không crash, chỉ là không có cross-DP benefit cho các pool đó.

**6. Không kết hợp với `shm_cross_dp`**
`shm_peer_l2` tự thiết lập shared L2 allocator. Chỉ cần một flag duy nhất.

---

## 10. Tham khảo

- Implementation: `hicache_shm_peer_l2.py` (cùng thư mục)
- Shared allocator: `pool_host/common.py` — `ShmHostTensorAllocator`
- SHM file allocation: `storage/mmap/mmap_allocator.py` — `alloc_shm`
- L2 pool base: `pool_host/base.py` — `register_alloc_callback`, slot partitioning
- Cache controller: `hiradix_cache.py` — `write_backup`, `prefetch_from_storage`
