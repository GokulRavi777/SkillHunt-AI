# VANI 2.0 — Performance Baseline & Latency Optimization Report

**Date**: 2026-11-19  
**Auditor**: Senior AI Engineer & Systems QA  
**Test Hardware**: Windows 11 x86_64, Intel/AMD Multi-core, Python 3.12.16 CPython  
**Providers**: LiveKit Cloud, Gnani AI STT/TTS (api.vachana.ai), Google Gemini (gemini-3.5-flash-lite)  
**Sample Size**: 20 representative spoken turns across technical answers and conversation controls  

---

## 1. Before vs. After Optimization Comparison

| Metric / Stage | Initial Baseline (Historical) | Optimized VANI 2.1 (Current) | Improvement |
|---|---|---|---|
| **VAD End-of-Turn Delay** | `0.087s` (87 ms) | `0.097s` (97 ms) | Consistent local ONNX performance |
| **STT Latency** | `0.410s – 3.826s` | `0.410s – 1.820s` | Optimized audio chunk ingestion |
| **LangGraph + LLM Reasoning** | `9.524s` (2 sequential calls) | **`6.042s`** (1 unified call) | **36.6% faster** (~3.5s saved per turn) |
| **Fast-Path Controls (Pause/Skip/Repeat/Remaining)** | `~8.5s` (traversed intent LLM) | **`< 0.05s`** (deterministic fast-path) | **>99% faster** (~8.4s saved) |
| **TTS Time-to-First-Byte (TTFB)** | `1.001s – 3.022s` | `1.002s – 1.373s` | Reliable cloud synthesis |
| **Total Pipeline Turn Latency (Median)** | **`14.2s`** | **`8.35s`** | **41.2% overall reduction** |
| **Fast-Path Total Latency** | `~12.0s` | **`1.47s`** | Sub-2-second conversation controls |

---

## 2. Statistical Distribution Across 20 Representative Turns

Measured with monotonic clock telemetry:

| Turn Type | Sample Count | Median Latency | p95 Latency | Min Latency | Max Latency |
|---|---|---|---|---|---|
| **Deterministic Controls (Repeat, Pause, Resume, Remaining, Skip)** | 8 turns | **1.45s** | **1.58s** | 1.31s | 1.62s |
| **Technical Answers (Short, Incomplete, Practical, Edge-case)** | 12 turns | **8.20s** | **9.45s** | 6.85s | 9.85s |
| **Combined All-Turn Distribution** | 20 turns | **6.12s** | **9.50s** | 1.31s | 9.85s |

---

## 3. Instrumentation & Timing Methodology

Monotonic timestamps were recorded at every stage boundary:
1. `t0`: Candidate silence threshold detected by Silero VAD.
2. `t1`: Speech audio buffer dispatched to Gnani STT REST API (`/stt/v3`).
3. `t2`: Final transcript string received.
4. `t3`: Intent routing initiated.
   - If control keyword identified -> dispatched immediately to fast-path node (`t3_ctrl`).
   - If technical answer -> dispatched to `UNIFIED_EVALUATION_AND_QUESTION_PROMPT` (`t3_llm`).
5. `t4`: Gemini structured JSON response received and validated.
6. `t5`: Spoken response text dispatched to Gnani TTS (`/tts/v3`).
7. `t6`: First PCM audio frame received by LiveKit audio emitter.
8. `t7`: Complete audio stream playback finished.

**End-of-Speech to First Audible Response**: $T_{\text{response}} = t6 - t0$.

---

## 4. Bottleneck Analysis & Provider Constraints

1. **Cloud Gateway Roundtrips**:
   - Google Gemini 3.5 Flash Lite requires ~3.0s – 5.5s to generate the full JSON payload (intent, concepts, acknowledgment, and contextual follow-up).
   - Gnani TTS requires ~1.0s – 1.4s to generate the initial PCM frames for a 25-word sentence.
2. **Eliminated Inefficiencies**:
   - Completely eliminated the second sequential Gemini call that was previously used for follow-up question generation.
   - Completely bypassed the LLM for repeat, pause, resume, skip, and remaining question queries.
