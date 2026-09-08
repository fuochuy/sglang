"""Generate HiCache shm_peer_l2 technical PDF documentation."""
from __future__ import annotations
import sys
sys.path.insert(0, "/Users/lap15741/Library/Python/3.9/lib/python/site-packages")

from fpdf import FPDF
from fpdf.enums import XPos, YPos

# -- palette ------------------------------------------------------------------
C_BLACK  = (18,  18,  18)
C_WHITE  = (255, 255, 255)
C_BLUE   = (30,  90, 160)
C_BLUE_L = (210, 228, 248)
C_GRAY   = (100, 100, 100)
C_GRAY_L = (245, 245, 245)
C_GRAY_M = (210, 210, 210)
C_GREEN  = (34,  139,  34)
C_RED    = (180,  30,  30)
C_ORANGE = (200, 100,   0)
C_YELLOW = (255, 243, 195)
C_MONO   = (40,  40,  40)


class PDF(FPDF):
    def __init__(self):
        super().__init__("P", "mm", "A4")
        self.set_margins(22, 20, 22)
        self.set_auto_page_break(True, margin=22)

    # -- helpers ---------------------------------------------------------------

    def _rgb(self, triplet):
        return triplet[0], triplet[1], triplet[2]

    def set_fg(self, c): self.set_text_color(*self._rgb(c))
    def set_bg(self, c): self.set_fill_color(*self._rgb(c))
    def set_ln(self, c): self.set_draw_color(*self._rgb(c))

    def body(self, size=10):
        self.set_font("Helvetica", size=size)
        self.set_fg(C_BLACK)

    def mono(self, size=8.5):
        self.set_font("Courier", size=size)
        self.set_fg(C_MONO)

    def h1(self, text):
        self.ln(3)
        self.set_fg(C_WHITE)
        self.set_bg(C_BLUE)
        self.set_font("Helvetica", "B", 13)
        self.cell(0, 8, f"  {text}", fill=True,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)
        self.body()

    def h2(self, text):
        self.ln(2)
        self.set_font("Helvetica", "B", 11)
        self.set_fg(C_BLUE)
        self.cell(0, 6, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_ln(C_BLUE)
        self.line(self.get_x(), self.get_y(), self.get_x() + 166, self.get_y())
        self.ln(2)
        self.body()

    def h3(self, text):
        self.ln(1)
        self.set_font("Helvetica", "B", 10)
        self.set_fg(C_BLACK)
        self.cell(0, 5.5, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.body()

    def para(self, text, size=10):
        self.body(size)
        self.multi_cell(0, 5.5, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def code_block(self, lines: list[str], size=7.5):
        self.set_bg(C_GRAY_L)
        self.set_ln(C_GRAY_M)
        x, y = self.get_x(), self.get_y()
        max_w = 166
        line_h = 4.5
        total_h = len(lines) * line_h + 4
        self.rect(x, y, max_w, total_h, style="FD")
        self.set_xy(x + 2, y + 2)
        self.mono(size)
        for line in lines:
            self.cell(0, line_h, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)
        self.body()

    def bullet(self, text, indent=4, size=10):
        self.body(size)
        x = self.get_x()
        self.set_x(x + indent)
        self.set_fg(C_BLUE)
        self.cell(4, 5.5, "•")
        self.set_fg(C_BLACK)
        self.multi_cell(0, 5.5, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_x(x)

    def kv_row(self, label, value, label_w=52):
        self.set_font("Helvetica", "B", 9.5)
        self.set_fg(C_BLACK)
        self.cell(label_w, 5.5, label)
        self.set_font("Helvetica", size=9.5)
        self.set_fg(C_GRAY)
        self.multi_cell(0, 5.5, value, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_fg(C_BLACK)

    def note_box(self, text, color=C_YELLOW, border=C_ORANGE):
        self.set_bg(color)
        self.set_ln(border)
        x, y = self.get_x(), self.get_y()
        lines = self.multi_cell(0, 5.5, text,
                                new_x=XPos.LMARGIN, new_y=YPos.NEXT,
                                dry_run=True, output="LINES")
        h = len(lines) * 5.5 + 5
        self.rect(x, y, 166, h, style="FD")
        self.set_xy(x + 3, y + 2.5)
        self.body(9.5)
        self.set_fg(C_MONO)
        self.multi_cell(160, 5.5, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)
        self.body()

    def table_header(self, cols: list[tuple[str, float]]):
        self.set_bg(C_BLUE)
        self.set_fg(C_WHITE)
        self.set_font("Helvetica", "B", 9)
        for label, w in cols:
            self.cell(w, 6, f" {label}", fill=True)
        self.ln()
        self._table_cols = cols

    def table_row(self, cells: list[str], shade=False):
        self.set_bg(C_GRAY_L if shade else C_WHITE)
        self.set_fg(C_BLACK)
        self.set_font("Helvetica", size=9)
        for (_, w), text in zip(self._table_cols, cells):
            self.cell(w, 6, f" {text}", fill=shade, border="B")
        self.ln()

    # -- header/footer ---------------------------------------------------------

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_fg(C_GRAY)
        self.cell(0, 8, "HiCache shm_peer_l2 - Technical Reference",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_ln(C_GRAY_M)
        self.line(22, self.get_y(), 188, self.get_y())
        self.ln(2)

    def footer(self):
        self.set_y(-16)
        self.set_ln(C_GRAY_M)
        self.line(22, self.get_y(), 188, self.get_y())
        self.ln(1)
        self.set_font("Helvetica", "I", 8)
        self.set_fg(C_GRAY)
        self.cell(0, 6, f"Page {self.page_no()}", align="C")


# ═══════════════════════════════════════════════════════════════════════════════
def build_cover(pdf: PDF):
    pdf.add_page()
    pdf.set_bg(C_BLUE)
    pdf.rect(0, 0, 210, 80, style="F")

    pdf.set_xy(22, 24)
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_fg(C_WHITE)
    pdf.cell(0, 12, "HiCache shm_peer_l2", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_x(22)
    pdf.set_font("Helvetica", size=14)
    pdf.set_fg(C_BLUE_L)
    pdf.cell(0, 8, "Cross-DP Peer L2 Cache - Technical Reference",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_xy(22, 82)
    pdf.body(10)
    pdf.set_fg(C_GRAY)

    pdf.set_font("Helvetica", size=10)
    pdf.set_fg(C_BLACK)
    pdf.ln(4)
    pdf.para(
        "This document provides a deep-dive into the shm_peer_l2 storage backend for "
        "SGLang HiCache. It covers physical memory layout, the full read/write/eviction "
        "lifecycle, generation-counter stale-detection, and a comparison with alternative "
        "backends, to help engineers configure and operate the system correctly."
    )

    # quick-facts box
    pdf.set_bg(C_BLUE_L)
    pdf.set_ln(C_BLUE)
    pdf.rect(22, pdf.get_y(), 166, 46, style="FD")
    pdf.set_xy(25, pdf.get_y() + 3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fg(C_BLUE)
    pdf.cell(0, 6, "Quick Facts", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(25)
    facts = [
        ("Backend flag",      "--hicache-storage-backend shm_peer_l2"),
        ("Requires",          "dp_size >= 2, all ranks on the same node"),
        ("Write policy",      "write_through (mandatory)"),
        ("L2 allocator",      "shm_shared_l2 (set automatically)"),
        ("Index entry size",  "288 bytes per key"),
        ("Default capacity",  "page_num x 4 (auto-computed at startup)"),
    ]
    for label, val in facts:
        pdf.kv_row(label, val, label_w=48)


# ═══════════════════════════════════════════════════════════════════════════════
def build_overview(pdf: PDF):
    pdf.add_page()
    pdf.h1("1  Overview")

    pdf.para(
        "shm_peer_l2 allows multiple DP ranks running on the same node to share their "
        "L2 host KV cache without copying data through a separate L3 store. Both ranks "
        "map the same physical shared-memory (SHM) pages via mmap(MAP_SHARED); when "
        "Rank A finishes computing a prefix and flushes KV data into L2, Rank B can "
        "read it directly from the shared buffer using a single in-RAM memcpy."
    )

    pdf.h2("1.1  Motivation")
    pdf.para(
        "In a multi-DP deployment each DP rank independently manages GPU memory "
        "(L1) and host memory (L2). Without sharing, when Rank A has already computed "
        "prefix P and flushed it to L2, Rank B receiving the same prefix must recompute "
        "it from scratch. shm_peer_l2 eliminates this redundant computation by giving "
        "Rank B a fast path: a 288-byte index lookup + a ~10 MB in-RAM copy instead "
        "of hundreds of GPU FLOPS."
    )

    pdf.h2("1.2  Conceptual diagram")
    pdf.code_block([
        "  Without shm_peer_l2:",
        "    Rank A: [GPU L1] --> [L2 buffer A]   <-- private, Rank B cannot see it",
        "    Rank B: [GPU L1] --> [L2 buffer B]   <-- must recompute same prefix",
        "",
        "  With shm_peer_l2:",
        "    Rank A: [GPU L1] --> [Shared L2 SHM buffer]",
        "    Rank B: [GPU L1] <-- memcpy --------- [Shared L2 SHM buffer][Rank A slot]",
        "                          ^",
        "                          No recompute needed",
    ])

    pdf.h2("1.3  Comparison with sibling backends")
    pdf.table_header([
        ("Property",        44),
        ("shm_cross_dp",    55),
        ("shm_peer_l2",     55),
    ])
    rows = [
        ("L2 buffer",       "Shared physical pages",    "Shared physical pages"),
        ("L3 data store",   "SHM file (full copy)",     "None"),
        ("Write path",      "GPU->L2->copy to L3",      "GPU->SHM L2->288B pointer"),
        ("Read path",       "L3->L2->GPU",              "memcpy in SHM->GPU"),
        ("Extra RAM",       "L2 + L3 data copy",        "L2 + tiny index (~55 MB)"),
        ("Interface",       "v0 batch_set/batch_get",   "v1 zero-copy v1 interface"),
        ("Latency",         "Higher (extra L3 hop)",    "Lower (one memcpy in RAM)"),
    ]
    for i, r in enumerate(rows):
        pdf.table_row(list(r), shade=(i % 2 == 0))
    pdf.ln(2)

    pdf.note_box(
        "NOTE: Both backends use the same shm_shared_l2 allocator for the L2 buffer. "
        "Specifying --hicache-storage-backend shm_peer_l2 automatically activates the "
        "shared allocator; you do NOT need to also set shm_cross_dp."
    )


# ═══════════════════════════════════════════════════════════════════════════════
def build_memory(pdf: PDF):
    pdf.add_page()
    pdf.h1("2  Physical Memory Layout")

    pdf.h2("2.1  SHM buffer creation at startup")
    pdf.para(
        "During HiRadixCache initialisation, the allocator type is resolved to "
        "shm_shared_l2 because the backend is shm_peer_l2. A deterministic SHM "
        "file name is computed from the model slug and PP rank so that every DP "
        "process maps the same file:"
    )
    pdf.code_block([
        "shm_name = 'sglang_l2_{model_slug}_pp{pp_rank}_{pp_size}'",
        "",
        "# mmap_allocator.py: _open_named_shm_fd()",
        "flock(lock_fd, LOCK_EX)",
        "fd = open('/dev/shm/{shm_name}.mmap', O_CREAT|O_RDWR)",
        "if is_new: ftruncate(fd, alloc_bytes)   # only the first rank does this",
        "flock(lock_fd, LOCK_UN)",
        "",
        "mm  = mmap.mmap(fd, alloc_bytes, flags=MAP_SHARED|MAP_POPULATE)",
        "mm.madvise(MADV_POPULATE_WRITE)          # pre-fault all pages now",
        "tensor = torch.frombuffer(mm)            # zero-copy tensor view",
    ])
    pdf.para(
        "MAP_SHARED causes the kernel to map both processes' virtual addresses to "
        "the same physical page frames. MAP_POPULATE + MADV_POPULATE_WRITE pre-fault "
        "all pages at startup so there are no page faults in the critical request path."
    )

    pdf.h2("2.2  Slot layout and partitioning")
    pdf.code_block([
        "page_num   = total_tokens // page_size + 1     # e.g. 47,683 pages",
        "local_pages= page_num // dp_size               # pages per DP rank",
        "local_size = local_pages * page_size           # tokens per rank",
        "",
        "Rank 0:  slot_start = 0            free_slots = [0 .. local_size-1]",
        "Rank 1:  slot_start = local_size   free_slots = [local_size .. 2*local_size-1]",
        "",
        "kv_buffer shape: (page_num, num_layers, 1, num_heads, head_dim)  [page_first layout]",
        "One page at slot s occupies kv_buffer[s // page_size, :, :, :, :]",
    ])
    pdf.para(
        "Slot indices are absolute token-level offsets within the shared buffer. "
        "Each rank only allocates/frees slots within its own partition, but any "
        "rank can READ from any absolute slot because the buffer is fully shared."
    )

    pdf.h2("2.3  Files on /dev/shm")
    pdf.table_header([("File", 100), ("Size", 30), ("Purpose", 36)])
    file_rows = [
        ("sglang_l2_{model}_pp{r}_{s}.mmap",     "~L2 size (GB)", "Shared KV buffer"),
        ("sglang_l2_{model}_pp{r}_{s}.mmap.lock","<1 KB",         "flock serialise creation"),
        ("sglang_l2_idx_{model}_pp{r}_{s}.bin",  "~55 MB",        "Index hash table (288B/entry)"),
        ("sglang_l2_idx_{model}_pp{r}_{s}.bin.lock","<1 KB",      "flock for index writes"),
        ("sglang_l2_gen_{model}_pp{r}_{s}.bin",  "~0.18 MB",      "Generation counters (4B/page)"),
        ("sglang_l2_gen_{model}_pp{r}_{s}.bin.lock","<1 KB",      "flock for gen SHM creation"),
    ]
    for i, r in enumerate(file_rows):
        pdf.table_row(list(r), shade=(i % 2 == 0))
    pdf.ln(2)

    pdf.h2("2.4  Index entry structure (288 bytes each)")
    pdf.code_block([
        "Offset  Size   Field     Description",
        "------  -----  --------  ----------------------------------------------",
        "0       1 B    valid     0=empty, 1=valid (written last as visibility fence)",
        "1       1 B    dp_rank   which DP rank wrote this entry",
        "2       4 B    gen       generation counter at write time (uint32 LE)",
        "6       2 B    pad",
        "8       8 B    slot_idx  first token index in host pool (uint64 LE)",
        "16      8 B    hash64    low-8 bytes of SHA-256(key) (uint64 LE)",
        "24      2 B    key_len   length of key string (uint16 LE)",
        "26      6 B    pad",
        "32     256 B   key_str   UTF-8 encoded key (zero-padded)",
    ])


# ═══════════════════════════════════════════════════════════════════════════════
def build_lifecycle(pdf: PDF):
    pdf.add_page()
    pdf.h1("3  Cache Lifecycle")

    pdf.h2("3.1  Write path - Rank A processes a new request (cache miss)")

    pdf.h3("Step 1: GPU compute -> L1 (GPU HBM)")
    pdf.para(
        "The prefix is absent from L1. The GPU computes attention and stores the "
        "resulting KV tensors into the device pool (MHATokenToKVPool). A RadixCache "
        "TreeNode is created with node.value = device_indices."
    )

    pdf.h3("Step 2: _inc_hit_count triggers write-through")
    pdf.code_block([
        "# hiradix_cache.py:988",
        "def _inc_hit_count(self, node):",
        "    node.hit_count += 1",
        "    if not node.backuped and node.hit_count >= write_through_threshold:  # =1",
        "        self.write_backup(node)   # triggered immediately on first hit",
    ])

    pdf.h3("Step 3: write_backup - GPU DMA to L2 SHM")
    pdf.code_block([
        "host_indices = mem_pool_host.alloc(len(device_indices))",
        "#   -> takes slots from Rank A's partition of the shared buffer",
        "#   -> _alloc_callbacks fired: gen[page_idx]++",
        "",
        "cache_controller.write(device_indices, host_indices)",
        "#   -> cudaMemcpyAsync: GPU HBM[device_slots] -> SHM kv_buffer[host_slots]",
        "#   -> DMA is asynchronous; node.lock_ref++ prevents eviction during DMA",
        "",
        "node.host_value = host_indices.clone()",
        "node.backuped   = True   (after DMA ack)",
    ])

    pdf.h3("Step 4: backup_thread writes 288-byte pointer to index SHM")
    pdf.code_block([
        "# cache_controller.py backup_thread_func",
        "# page_set_func = _page_set_zero_copy  (shm_peer_l2 uses V1 interface)",
        "storage_backend.batch_set_v1(hash_values, host_indices)",
        "",
        "# hicache_shm_peer_l2.py batch_set_v1",
        "slot_start = host_indices[i * page_size]",
        "gen        = gen_arr[slot_start // page_size]   # current generation",
        "row[E_VALID]  = 0   # invalidate first (readers see empty during update)",
        "row[E_DPRANK] = A",
        "row[E_GEN]    = gen",
        "row[E_SLOT]   = slot_start",
        "row[E_HASH]   = sha256(key)[:8]",
        "row[E_KEYSTR] = key.encode()[:256]",
        "row[E_VALID]  = 1   # set valid last = visibility fence",
    ])
    pdf.para(
        "Writing valid=0 first and valid=1 last means readers that observe valid=0 "
        "during the update will skip the entry safely. No extra lock is needed for readers "
        "between the two valid writes."
    )

    pdf.add_page()
    pdf.h2("3.2  Read path - Rank B requests the same prefix")

    pdf.h3("Step 1: Radix tree L1 miss -> prefetch_from_storage")
    pdf.para(
        "Rank B has a cache miss on L1. The prefetch thread is notified and begins "
        "querying storage for the prefix pages."
    )

    pdf.h3("Step 2: batch_exists_v2 - index lookup under LOCK_SH")
    pdf.code_block([
        "# hicache_shm_peer_l2.py batch_exists_v2",
        "fcntl.flock(lock_fd, LOCK_SH)   # shared: multiple readers allowed simultaneously",
        "for key in keys:",
        "    idx_slot = _find(key)        # hash64(key) % capacity",
        "    if idx_slot is None:  break  # not in index -> miss",
        "    if _entry_dp_rank(idx_slot) == self.dp_rank:  break  # own data",
        "    kv_pages += 1               # peer data -> hit",
        "fcntl.flock(lock_fd, LOCK_UN)",
        "",
        "# result: storage_hit_count = kv_pages * page_size",
        "# scheduler allocates host_indices in Rank B's partition",
    ])

    pdf.h3("Step 3: batch_get_v1 Phase 1 - read peer slot + generation check")
    pdf.code_block([
        "fcntl.flock(lock_fd, LOCK_SH)",
        "for key in keys:",
        "    idx_slot   = _find(key)                      # 288B read from index SHM",
        "    peer_slot  = _entry_slot_idx(idx_slot)       # Rank A's absolute slot",
        "    stored_gen = _entry_generation(idx_slot)     # gen at write time",
        "    curr_gen   = gen_arr[peer_slot // page_size] # current gen",
        "    if stored_gen != curr_gen:",
        "        peer_slots.append(None); continue        # stale -> miss",
        "    peer_slots.append(peer_slot)                 # valid hit",
        "fcntl.flock(lock_fd, LOCK_UN)",
    ])

    pdf.h3("Step 4: batch_get_v1 Phase 2 - memcpy within SHM (no lock)")
    pdf.code_block([
        "for i, peer_slot in enumerate(peer_slots):",
        "    page_data  = pool.get_data_page(peer_slot)  # view of Rank A's physical page",
        "    local_slot = host_indices[i * page_size]    # Rank B's own slot",
        "    pool.set_from_flat_data_page(local_slot, page_data)",
        "    # -> torch.Tensor copy: ~10 MB for a page, entirely in RAM",
        "    # -> both tensors are views of the same mmap -> kernel uses optimised DRAM copy",
    ])

    pdf.h3("Step 5: GPU DMA L2 -> L1")
    pdf.para(
        "After the memcpy Rank B has valid KV data in its own partition at "
        "host_indices. The cache controller issues cudaMemcpyAsync to move it "
        "from SHM RAM to GPU HBM. The prefix compute step is skipped entirely."
    )

    pdf.note_box(
        "Cost summary for Rank B:\n"
        "  1 x index lookup  (288B LOCK_SH read from /dev/shm)\n"
        "  1 x memcpy in RAM (~10 MB per page, no GPU involved)\n"
        "  1 x DMA  (SHM -> GPU HBM, same as a normal L2 load)\n"
        "  0 x GPU FLOPs for the prefix"
    )


# ═══════════════════════════════════════════════════════════════════════════════
def build_gen_counter(pdf: PDF):
    pdf.add_page()
    pdf.h1("4  Generation Counter - Stale Data Prevention")

    pdf.para(
        "The generation counter array (sglang_l2_gen_*.bin) contains one uint32 "
        "per page slot. Each time a slot is reallocated by Rank A the counter "
        "for that slot increments. Rank B compares the stored generation in the "
        "index entry against the live counter before copying; a mismatch means "
        "the slot has been reused since the entry was written."
    )

    pdf.h2("4.1  Timeline showing race without counter")
    pdf.code_block([
        "t1: Rank A alloc slot S, writes KV for prefix P1",
        "t2: Rank A writes index: (P1 -> slot=S, gen=0)",
        "t3: Rank A evicts P1, frees slot S   (host memory pressure)",
        "t4: Rank A allocs slot S again for prefix P2",
        "    [without counter]: slot is overwritten with P2 data",
        "t5: Rank B looks up P1 in index -> (slot=S, gen=0)",
        "    [without counter]: copies P2 data, thinks it is P1 -> SILENT CORRUPTION",
    ])

    pdf.h2("4.2  Timeline with counter")
    pdf.code_block([
        "t4: Rank A allocs slot S",
        "    -> _alloc_callback fires: gen_arr[S // page_size] += 1   # gen = 1",
        "t5: Rank B looks up P1 in index -> (slot=S, stored_gen=0)",
        "    -> curr_gen = gen_arr[S // page_size] = 1",
        "    -> 0 != 1 -> MISS  (correct: data is gone)",
    ])

    pdf.h2("4.3  Atomicity guarantee")
    pdf.para(
        "gen_arr[i] += 1 is an aligned 32-bit store. On x86-64 and ARM64, "
        "an aligned word store is naturally atomic (single bus transaction). "
        "Rank B reads the counter with only an LOCK_SH flock - the flock "
        "provides a memory barrier ensuring Rank B sees the updated counter "
        "after Rank A's allocation. No additional mutex is needed."
    )

    pdf.h2("4.4  Counter initialisation")
    pdf.para(
        "The gen array SHM file is created with all zeros. The counter for a "
        "slot only ever increases, never resets (uint32 wraps after ~4 billion "
        "reallocations, which is effectively never in practice). Stale files "
        "from a previous run are detected by size mismatch and recreated."
    )


# ═══════════════════════════════════════════════════════════════════════════════
def build_eviction(pdf: PDF):
    pdf.add_page()
    pdf.h1("5  Eviction")

    pdf.para(
        "There are two independent eviction levels: L1 (GPU HBM) and L2 (host SHM). "
        "Both are triggered by memory pressure when allocation fails."
    )

    pdf.h2("5.1  L1 eviction (GPU -> L2 demotion)")
    pdf.para(
        "When GPU memory is full, the eviction algorithm (LRU-based heap over "
        "evictable_leaves) selects leaf nodes. For nodes that are already backuped "
        "(have host_value), eviction simply frees the device slots:"
    )
    pdf.code_block([
        "# _evict_backuped",
        "cache_controller.evict_device(device_indices)  # -> free GPU slots",
        "node.value   = None",
        "node.evicted = True",
        "# node.host_value is preserved -> node enters DEMOTED state",
        "# -> future request can load_back (L2->L1) without recompute",
    ])
    pdf.para(
        "For nodes not yet backuped (write_through mode), they are simply dropped "
        "(GPU slots freed, no host copy). Under write_back mode, eviction will "
        "trigger a DMA to L2 first."
    )

    pdf.h2("5.2  L2 eviction (SHM host -> gone)")
    pdf.para(
        "When the host SHM pool is full, evict_host selects nodes from "
        "evictable_host_leaves (nodes that are GPU-evicted, not locked, and are "
        "leaves in the backup tree):"
    )
    pdf.code_block([
        "# hiradix_cache.py evict_host",
        "for x in eviction_heap:                         # LRU-ordered",
        "    if x.evicted and x.host_ref_counter == 0:",
        "        cache_controller.evict_host(x.host_value)",
        "        # -> mem_pool_host.free(host_indices)  <- slots returned to free list",
        "        # -> DOES NOT touch gen_arr here",
        "        node removed from Radix tree entirely",
    ])

    pdf.h2("5.3  Gen counter and L2 eviction interaction")
    pdf.para(
        "When a slot is freed (evict_host) and then reallocated by the next "
        "alloc() call, the _alloc_callback fires gen_arr[slot]++. This happens "
        "before any new data is written to the slot. So Rank B seeing the old "
        "index entry will detect the mismatch and treat it as a miss, "
        "regardless of whether eviction happened before or after the index "
        "entry was written."
    )

    pdf.note_box(
        "Index entries are NEVER explicitly deleted on L2 eviction. They become "
        "implicitly stale via the generation counter. The entry will be physically "
        "overwritten only when a new key hashes to the same index slot."
    )

    pdf.h2("5.4  State machine summary")
    pdf.code_block([
        "  [compute done]                     [L1 evict, backuped=True]",
        "  ABSENT ---------> LIVE_GPU ------> DEMOTED",
        "                       |  ^               |",
        "                       |  | load_back     | [L2 evict]",
        "                       |  |               v",
        "                       |  +----------  GONE",
        "                       |",
        "                       v [L1 evict, not backuped]",
        "                     GONE",
    ])


# ═══════════════════════════════════════════════════════════════════════════════
def build_pros_cons(pdf: PDF):
    pdf.add_page()
    pdf.h1("6  Advantages and Disadvantages")

    pdf.h2("6.1  Advantages")

    pros = [
        ("No L3 store needed",
         "Unlike shm_cross_dp, mooncake, nixl - there is no separate L3 copy of "
         "the KV data. The shared L2 buffer IS the store. This eliminates an "
         "entire memory copy and halves the disk/network I/O."),
        ("Minimal overhead memory",
         "Extra RAM is only the index (~55 MB) and gen array (~0.2 MB) for a "
         "475 GB L2 pool. shm_cross_dp would need another 475 GB for the L3 copy."),
        ("Very low read latency",
         "A peer cache hit costs one index lookup (288B read) + one in-RAM memcpy "
         "compared to a disk or network round-trip for file/nixl/mooncake backends."),
        ("Zero GPU FLOPs for prefix",
         "Rank B skips prefix computation entirely. The speedup scales with the "
         "length of the shared prefix."),
        ("No network required",
         "Everything is within a single node's RAM. No RDMA, no NVLink, no MPI."),
        ("Automatic shared allocator",
         "Specifying shm_peer_l2 is sufficient; the shm_shared_l2 allocator is "
         "wired up automatically."),
        ("Lock-free read data path",
         "Phase 2 of batch_get_v1 (the actual memcpy) runs without any lock. "
         "Only the index lookup in Phase 1 uses a shared read lock (LOCK_SH), "
         "which allows multiple concurrent readers."),
    ]
    for title, body in pros:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fg(C_GREEN)
        pdf.cell(5, 5.5, "+")
        pdf.set_fg(C_BLACK)
        pdf.cell(0, 5.5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.body(9.5)
        pdf.set_x(pdf.get_x() + 7)
        pdf.set_fg(C_GRAY)
        pdf.multi_cell(159, 5, body, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)

    pdf.h2("6.2  Disadvantages and Constraints")
    pdf.ln(1)

    cons = [
        ("Same node only",
         "shm_peer_l2 relies on /dev/shm which is a node-local tmpfs. Across "
         "nodes, use mooncake or nixl instead."),
        ("write_through mandatory",
         "write_back only flushes L2 on L1 eviction. Rank B may not see Rank A's "
         "data for minutes. write_through must be enabled, which increases "
         "per-request host memory pressure slightly."),
        ("Rank B must wait for Rank A's backup_thread",
         "The index entry is written asynchronously after the GPU DMA completes. "
         "If Rank B receives the same prefix before Rank A's backup_thread has "
         "finished, it will cache-miss and recompute. This window is typically "
         "milliseconds under write_through."),
        ("Direct-mapped index collisions",
         "The index is a direct-mapped hash table: two keys with the same "
         "hash64 % capacity will collide and the older entry is evicted silently. "
         "Under-sizing peer_l2_capacity increases the miss rate. The server logs "
         "collision statistics every 10,000 writes."),
        ("No cross-rank invalidation",
         "If Rank A's L2 slot is evicted, the stale index entry is not removed. "
         "Rank B detects staleness via the generation counter, but the entry "
         "occupies an index slot until overwritten by a hash collision."),
        ("No L2 hit for same rank",
         "Rank B cannot use shm_peer_l2 to read its own data (the dp_rank check "
         "filters self-hits). Each rank's own L2 data is accessed through the "
         "standard L2 load path, not through the peer index."),
        ("SHM /dev/shm sizing in containers",
         "Docker containers default to 64 MB for /dev/shm. A 475 GB L2 pool "
         "requires setting --shm-size=500g and -v /dev/shm:/dev/shm explicitly."),
        ("No prefetch guarantee",
         "batch_exists_v2 counts pages in the index but does not guarantee that "
         "the data is still valid at batch_get_v1 time. A generation mismatch "
         "between the two calls causes a miss and the prefetched host slot is "
         "wasted. This is a best-effort cache, not a guaranteed transfer."),
    ]
    for title, body in cons:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fg(C_RED)
        pdf.cell(5, 5.5, "-")
        pdf.set_fg(C_BLACK)
        pdf.cell(0, 5.5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.body(9.5)
        pdf.set_x(pdf.get_x() + 7)
        pdf.set_fg(C_GRAY)
        pdf.multi_cell(159, 5, body, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)


# ═══════════════════════════════════════════════════════════════════════════════
def build_config(pdf: PDF):
    pdf.add_page()
    pdf.h1("7  Configuration")

    pdf.h2("7.1  Required flags")
    pdf.code_block([
        "python -m sglang.launch_server \\",
        "    --model-path <model>                                  \\",
        "    --tp-size <tp>    --dp-size 2                         \\",
        "    --hicache-size <L2_GB>                                \\",
        "    --hicache-write-policy write_through                  \\",
        "    --hicache-io-backend kernel                           \\",
        "    --hicache-mem-layout page_first                       \\",
        "    --hicache-storage-backend shm_peer_l2",
        "",
        "# H200 / CUDA 12.8+ (cudaMemcpyBatchAsync available):",
        "    --hicache-io-backend direct                           \\",
        "    --hicache-mem-layout page_first_direct",
        "",
        "# Custom index capacity and directory:",
        "    --hicache-storage-backend-extra-config '{\"peer_l2_capacity\": 262144}'",
    ])

    pdf.h2("7.2  Extra config keys")
    pdf.table_header([("Key", 52), ("Default", 34), ("Description", 80)])
    pdf.table_row(["peer_l2_capacity", "page_num x 4 (auto)", "Index hash table entry count"], shade=True)
    pdf.table_row(["peer_l2_shm_dir",  "/dev/shm",             "Directory for index and gen files"])
    pdf.ln(2)

    pdf.h2("7.3  Sizing peer_l2_capacity")
    pdf.para(
        "The index is direct-mapped: one entry per hash bucket. Setting capacity too "
        "low increases the collision rate, causing valid entries to be overwritten. "
        "The recommended load factor is 25% (capacity = page_num x 4)."
    )
    pdf.code_block([
        "# Python helper",
        "def calc_capacity(hicache_gb, page_size_tokens=32,",
        "                  num_layers=80, num_kv_heads=8, head_dim=128,",
        "                  dtype_bytes=2, load_factor_inv=4):",
        "    size_per_token  = head_dim * num_kv_heads * num_layers * dtype_bytes * 2",
        "    page_bytes      = size_per_token * page_size_tokens",
        "    page_num        = int(hicache_gb * 1e9 / page_bytes)",
        "    capacity        = page_num * load_factor_inv",
        "    index_mb        = capacity * 288 / 1024**2",
        "    print(f'page_num={page_num:,}  capacity={capacity:,}  index={index_mb:.1f} MB')",
        "",
        "# Example: Llama 70B (GQA 8 heads), bf16, 475 GB L2",
        "# page_num=47,683  capacity=190,732 -> round to 2^18=262,144  index=54.8 MB",
    ])

    pdf.h2("7.4  Docker / container setup")
    pdf.code_block([
        "# docker-compose.yaml",
        "services:",
        "  sglang:",
        "    shm_size: '500gb'           # must be >= L2 size + overhead",
        "    volumes:",
        "      - /dev/shm:/dev/shm       # share host /dev/shm across containers",
        "",
        "# docker run equivalent",
        "docker run --shm-size=500g -v /dev/shm:/dev/shm ...",
    ])
    pdf.note_box(
        "All containers hosting DP ranks on the same node must mount the HOST's "
        "/dev/shm via -v /dev/shm:/dev/shm. Without this, each container has its "
        "own /dev/shm namespace and the shared mmap cannot be established."
    )


# ═══════════════════════════════════════════════════════════════════════════════
def build_ops(pdf: PDF):
    pdf.add_page()
    pdf.h1("8  Operations Guide")

    pdf.h2("8.1  Verify at startup")
    pdf.code_block([
        "# 1. Confirm shared buffer and index files are present",
        "ls -lh /dev/shm/sglang_l2*",
        "# Expected: 1 large .mmap (L2 size), 2 small .bin files (index + gen)",
        "",
        "# 2. Check /dev/shm capacity",
        "df -h /dev/shm",
        "",
        "# 3. Check log for shared index creation/attachment",
        "grep 'HiCacheShmPeerL2' /path/to/sglang.log",
        "# Rank 0: 'created index /dev/shm/sglang_l2_idx_... capacity=262144'",
        "# Rank 1: 'attached to existing index /dev/shm/sglang_l2_idx_...'",
        "",
        "# 4. Auto-computed capacity log",
        "grep 'auto-computed peer_l2_capacity' /path/to/sglang.log",
        "",
        "# 5. Collision rate log (emitted every 10,000 writes)",
        "grep 'collision rate' /path/to/sglang.log",
        "# Warning logged if rate > 10% -> increase peer_l2_capacity",
    ])

    pdf.h2("8.2  Clean up SHM files")
    pdf.code_block([
        "# Files persist after server stop; SGLang auto-detects stale on restart.",
        "# To force-clean:",
        "rm -f /dev/shm/sglang_l2*",
    ])

    pdf.h2("8.3  Troubleshooting")
    pdf.table_header([("Symptom", 70), ("Cause", 50), ("Fix", 46)])
    rows = [
        ("AttributeError: HostPoolGroup\nhas no attribute dp_rank",
         "Old code before fix",
         "Rebuild image from\nlatest fork"),
        ("invalid choice: shm_peer_l2",
         "Container uses upstream\nimage, not fork",
         "Ensure image built from\nfork source"),
        ("Rank 1 log shows 'created'\ninstead of 'attached'",
         "Ranks use different\nshm_name (model slug mismatch)",
         "Check served_model_name\nis identical across ranks"),
        ("High collision rate > 10%",
         "peer_l2_capacity too small",
         "Increase to page_num x 8"),
        ("No peer hits even after\nwarm-up",
         "write_back policy;\nRank A not flushing",
         "Switch to write_through"),
        ("OSError: No space left\non /dev/shm",
         "shm_size too small\nin container",
         "Add --shm-size=<L2+buffer>"),
    ]
    for i, r in enumerate(rows):
        pdf.table_row(list(r), shade=(i % 2 == 0))
    pdf.ln(3)

    pdf.h2("8.4  Full data flow summary")
    pdf.code_block([
        "  EVENT              WHO      PHYSICAL ACTION",
        "  -------------------------------------------------------------------",
        "  Startup            Both     mmap(MAP_SHARED) -> same physical frames",
        "  GPU compute done   Rank A   alloc SHM slot, cudaMemcpy GPU->SHM",
        "  backup_thread      Rank A   write 288B entry to index SHM",
        "  Rank B lookup      Rank B   LOCK_SH + read 288B + check gen counter",
        "  Rank B copy        Rank B   memcpy in SHM: Rank A slot -> Rank B slot",
        "  Rank B DMA         Rank B   cudaMemcpy: SHM[Rank B slot] -> GPU HBM",
        "  L1 evict           Rank A   GPU slot freed; SHM slot kept; evicted=True",
        "  L2 evict           Rank A   SHM slot freed; next alloc: gen[slot]++",
        "  Rank B stale read  Rank B   stored_gen != curr_gen -> treat as miss",
    ])


# ═══════════════════════════════════════════════════════════════════════════════
def main():
    pdf = PDF()
    pdf.set_lang("vi")

    build_cover(pdf)
    build_overview(pdf)
    build_memory(pdf)
    build_lifecycle(pdf)
    build_gen_counter(pdf)
    build_eviction(pdf)
    build_pros_cons(pdf)
    build_config(pdf)
    build_ops(pdf)

    out = "/Users/lap15741/Desktop/sglang/shm_peer_l2_technical_reference.pdf"
    pdf.output(out)
    print(f"PDF written to: {out}")
    print(f"Pages: {pdf.page}")


if __name__ == "__main__":
    main()
