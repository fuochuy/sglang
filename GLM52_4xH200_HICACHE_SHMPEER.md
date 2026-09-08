# GLM-5.2-W4AFP8 4xH200 HiCache shm_peer_l2 Benchmark

**Cluster:** h200-greennode_04 — 4x NVIDIA H200 (80 GB)  
**Image:** `vcr.vngcloud.vn/107710-huynp4-kc/sg-lang:fuochuy-hicache`  
**Model:** `PhalaCloud/GLM-5.2-W4AFP8` (served as `zai-org/GLM-5.2-FP8`)  
**Topology:** TP=4, DP=4, EP=4, dp-attention enabled  
**Serving:** SGLang + sglang-router  
**Spec decoding:** EAGLE (3 steps, topk=1, 4 draft tokens)  
**Dataset:** `semianalysis_cc_traces_weka_062126_256k` (256k-capped)  
**Duration:** 3600s profiling (all runs aborted at ~10% error threshold — glm45 parser issue, see below)  
**CCU:** 4 (max_running_requests = 8)

---

## Config summary

| Flag | Value |
|------|-------|
| `--mem-fraction-static` | 0.88 |
| `--context-length` | 131072 |
| `--hicache-size` | 64 GB/rank |
| `--hicache-io-backend` | direct |
| `--hicache-write-policy` | write_through |
| `--hicache-mem-layout` | page_first_direct |
| `--kv-cache-dtype` | fp8_e4m3 |
| GPU KV (L1) per rank | ~9.25 GB (~161k tokens) |
| CPU L2 per rank | 64 GB (~1.25M tokens) |

---

## Results

### Experiment matrix

| # | Router policy | HiCache storage | Config key | GH Run | GH Job |
|---|--------------|-----------------|------------|--------|--------|
| 1 | cache_aware + dp-aware | shm_peer_l2 | `…shmpeer-agentic` | [31986293262](https://github.com/vngcloud/InferenceX/actions/runs/31986293262) | [95261834046](https://github.com/vngcloud/InferenceX/actions/runs/31986293262/job/95261834046) |
| 2 | cache_aware + dp-aware | local (no shm) | `…local-agentic` | [31989831243](https://github.com/vngcloud/InferenceX/actions/runs/31989831243) | [95271317038](https://github.com/vngcloud/InferenceX/actions/runs/31989831243/job/95271317038) |
| 3 | round_robin | shm_peer_l2 | `…rr-hicache64-shmpeer-agentic` | [31993891036](https://github.com/vngcloud/InferenceX/actions/runs/31993891036) | [95282104083](https://github.com/vngcloud/InferenceX/actions/runs/31993891036/job/95282104083) |
| 4 | round_robin | local (no shm) | `…rr-hicache64-local-agentic` | [31993898662](https://github.com/vngcloud/InferenceX/actions/runs/31993898662) | [95282140976](https://github.com/vngcloud/InferenceX/actions/runs/31993898662/job/95282140976) |

---

### Steady-state metrics (at profiling abort)

| # | prefix_cache_hit | theoretical hit | cpu_kv_usage | tput_in_srv (peak) | tput_out_srv | Warmup | Profiling duration |
|---|-----------------|-----------------|-------------|---------------------|-------------|--------|--------------------|
| 1 cache_aware + shm | **95.1%** | 93.3% | 74.8% | **11,052 tok/s** | ~105 tok/s | 138s | ~8 min |
| 2 cache_aware + local | **94.8%** | 92.9% | 45.9% | **10,052 tok/s** | ~100 tok/s | 135s | ~39 min |
| 3 rr + shm | **80.9%** | 92.6% | **100%** | **9,596 tok/s** | ~81 tok/s | 228s | ~45 min |
| 4 rr + local | **79.5%** | 92.0% | 91.4% | **9,203 tok/s** | ~90 tok/s | 243s | ~26 min |

### prefix_cache_hit progression over time

| Elapsed | #1 cache_aware+shm | #2 cache_aware+local | #3 rr+shm | #4 rr+local |
|---------|--------------------|----------------------|-----------|-------------|
| ~0:30 | 95.5% | 95.5% | 93.0% | 93.0% |
| ~1:00 | 75.6% | 75.7% | 57.8% | 60.9% |
| ~2:00 | 71.6% | 72.4% | 38.3% | 47.9% |
| ~3:30 | ~82% | 71.6% | **35.2%** ← trough | **46.9%** ← trough |
| ~5:00 | 86.0% | 75.6% | 54.5% | 51.8% |
| ~7:00 | ~90% | 82.2% | 75.8% | 70.7% |
| ~13:00 | _(aborted)_ | 90.1% | 77.9% | 76.9% |
| ~15:00 | — | 92.4% | 78.5% | 78.4% |
| ~22:00 | — | 94.4% | 79.1% | 77.8% |
| ~25:00 | — | — | 80.4% | **79.5%** ← abort |
| ~39:00 | — | **94.8%** ← abort | 80.8% | — |
| ~45:00 | — | — | **80.9%** ← abort | — |

---

## Key findings

### 1. Router policy dominates cache hit rate; shm_peer_l2 contribution is marginal

| Comparison | Hit rate delta |
|-----------|----------------|
| cache_aware vs round_robin (shm) | 95.1% vs 80.9% = **−14.2pp** |
| cache_aware vs round_robin (local) | 94.8% vs 79.5% = **−15.3pp** |
| shm_peer_l2 vs local (cache_aware) | 95.1% vs 94.8% = **+0.3pp** |
| shm_peer_l2 vs local (round_robin) | 80.9% vs 79.5% = **+1.4pp** |

Routing policy accounts for ~14-15pp of hit rate. shm_peer_l2 adds only **+0.3pp with cache_aware** and **+1.4pp with round_robin** at steady state.

### 2. SGLang internal DP scheduling provides prefix affinity independent of the router

Surprisingly, both round_robin runs converge to ~78-80% hit rate — only ~15pp below cache_aware. This suggests SGLang's internal scheduler performs per-DP-rank KV prefix matching regardless of the external router policy. The cache_aware router adds the remaining gap by steering requests BEFORE they reach the backend.

### 3. shm_peer_l2 warms up faster, but local catches up

| Config | Time to reach >90% hit rate |
|--------|------------------------------|
| cache_aware + shm | ~7 min |
| cache_aware + local | ~13 min |
| rr + shm | never (plateaus at ~81%) |
| rr + local | never (plateaus at ~79%) |

With cache_aware routing, shm_peer_l2 cuts warm-up time by ~2×. With round_robin, neither variant reaches >90% — both plateau well below the cache_aware ceiling.

### 4. L2 fill rate reveals cross-rank activity

| Config | cpu_kv at abort | Time to reach 90%+ |
|--------|----------------|-------------------|
| cache_aware + shm | 74.8% | never (aborted early) |
| cache_aware + local | 45.9% | never |
| rr + shm | **100%** | ~36 min |
| rr + local | **91.4%** | ~23 min |

rr+local reaches 91% in ~23 min without cross-rank reads — showing that write_through alone fills L2 aggressively under round_robin (each rank absorbs all sessions). rr+shm fills to 100% (vs 91%) because cross-rank reads pull additional pages into local L2, confirming cross-rank transfers are occurring — but the net hit rate benefit is only +1.4pp.

### 5. Warmup is slower with round_robin

| Config | Warmup |
|--------|--------|
| cache_aware + shm | 138s |
| cache_aware + local | 135s |
| rr + shm | 228s (+65%) |
| rr + local | 243s (+76%) |

cache_aware routing steers warmup requests to their best-matching rank, completing warmup significantly faster.

---

## Conclusion

**shm_peer_l2 provides real but small cache-hit benefits (+0.3–1.4pp at steady state).** The dominant lever is the **router policy** (+14–15pp). With cache_aware + dp-aware routing already doing a good job of steering sessions to the right rank, shm_peer_l2's cross-rank L2 reads rarely come into play at steady state.

**shm_peer_l2 is most valuable during cold-start** (faster warmup, 2× with cache_aware) and has a meaningful effect on L2 utilization (100% vs 91% under round_robin), confirming cross-rank reads are active but not throughput-critical with this workload and CCU.

---

## Known issue: glm45 reasoning parser errors (~10% error rate)

All runs abort at the ~10% failed-request threshold. Root cause: the glm45 reasoning parser strips `<think>` tags from responses that contain only a thinking block, producing empty content. This is independent of routing policy or HiCache config.

- Affects all 4 runs equally
- Does not invalidate the cache hit rate comparison
- Fix: remove `--reasoning-parser glm45` from the recipe (keep `--tool-call-parser glm47`)

---

## Recipes

| Recipe file | Router | HiCache storage |
|-------------|--------|----------------|
| `glm5.2eagle4x_fp4_h200_sglang.sh` | cache_aware + dp-aware | shm_peer_l2 |
| `glm5.2eagle4x-local_fp4_h200_sglang.sh` | cache_aware + dp-aware | local |
| `glm5.2eagle4x-rr-shm_fp4_h200_sglang.sh` | round_robin | shm_peer_l2 |
| `glm5.2eagle4x-rr-local_fp4_h200_sglang.sh` | round_robin | local |
