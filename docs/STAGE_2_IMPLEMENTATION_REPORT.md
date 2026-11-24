# VANI 2.0 — Stage 2 Implementation Report
## Technical Question Answering, Skip Management & FIFO Revisit Queue

**Date:** 2026-11-24  
**Project:** `examples/vani_interview/`  
**Status:** Complete & Fully Validated  

---

### 1. Executive Summary

Stage 2 of the VANI 2.0 Conversational Voice Interviewer has been implemented and verified. The technical question workflow, per-question skip disambiguation, independent per-question revisit allowances, strict FIFO revisit queue, 30-second answer timer with race condition protection, hint policy, single-clarification limit, and follow-up constraints have been integrated into the existing LiveKit Agents, LangGraph, and Gemini architecture.

---

### 2. Completed Capabilities

#### 2.1 Reusable Technical Question Engine
- **Primary Progression**: Q1 $\rightarrow$ Q2 $\rightarrow$ Q3 managed through a single reusable question engine rather than hardcoded workflows.
- **Evaluation**: Unified single-turn structured Gemini evaluation capturing relevance, technical correctness, completeness, conceptual understanding, missing concepts, and follow-up justification without leaking internal scores or rubrics.
- **Strict Limits**: Exactly 3 primary questions max; maximum 1 follow-up per eligible primary question; **Q3 has strictly zero follow-ups**.

#### 2.2 Per-Question Skip & Revisit Policy
- **Interactive Disambiguation**: When candidate indicates difficulty (*"I don't know"*, *"Can we skip this?"*, *"I want to come back to this later"*), Vani asks:
  > *"That's fine. Would you like to skip this question permanently or revisit it after the remaining questions?"*
- **Option A — Permanent Skip**:
  - Response: *"Alright. Let's move to the next question."*
  - Marked `SKIPPED_PERMANENTLY`.
  - Consumes primary question slot.
  - Never enqueued, never asked again.
- **Option B — Revisit Later**:
  - Response: *"Sure. We'll come back to this question after the remaining questions."*
  - Marked `SKIPPED_PENDING_REVISIT`.
  - Consumes primary question slot.
  - Enqueued in strict First-In-First-Out (`session.revisit_queue`).
- **Independent Per-Question Allowance**:
  - Each primary question (Q1, Q2, Q3) has its own independent revisit allowance (max 1 revisit per question).
  - Consuming Q1's revisit allowance does not impact Q2 or Q3.
  - Attempting to skip/revisit again during revisit is rejected deterministically:
    > *"This question has already used its revisit opportunity. We will move forward."*
    Marked `REVISITED_UNANSWERED` and advances to next queued item or conclusion.

#### 2.3 Strict FIFO Revisit Queue Processing
- **Queue Timing**: Queued questions are processed strictly after all primary questions are completed/resolved.
- **Delivery Phrasing**:
  > *"Let's return to the question about [topic]. [Original question text]"*
- **Revisit Constraints**:
  - Revisit answers do NOT generate follow-ups.
  - The interview cannot conclude while eligible questions remain in `revisit_queue`.
  - Empty revisit queue concludes interview immediately after Q3.

#### 2.4 Answer Timer (30s) & Race-Condition Safeguards
- 30-second answer timer starting strictly after question playback completes.
- State-machine tracking: `WAITING_FOR_ANSWER` $\rightarrow$ `ANSWER_CAPTURE_IN_PROGRESS` $\rightarrow$ `ANSWER_RECEIVED`.
- Timer cancelled immediately upon candidate speech detection.
- Expiration response:
  > *"I understand you weren't able to provide an answer within the allotted time. Let's move on to the next question."*
  Marked `UNANSWERED_TIMEOUT`, consumes primary slot, no follow-up, no auto-revisit.

#### 2.5 Clarification, Example & Hint Policies
- **Clarification / Example**: Maximum 1 clarification/example per primary question. Subsequent requests politely declined:
  > *"I have already provided an example for this question. Please give it your best try, or let me know if you would like to skip it."*
- **Hints Disabled**: Requests for hints are politely declined without incrementing clarification or off-topic counters:
  > *"I can't provide hints during the assessment, but you can give it a try or choose to skip the question."*
- **Remaining Questions Inquiry**: UC31 returns remaining primary questions and separately details queued revisit questions.

#### 2.6 Universal Off-Topic Policy Preservation
- Continuous 3-tier off-topic enforcement across Stage 1 and Stage 2:
  1. 1st Off-topic $\rightarrow$ Redirect (*"I'm here to conduct your interview. Can we proceed?"*)
  2. 2nd Off-topic $\rightarrow$ Formal Warning
  3. 3rd Off-topic $\rightarrow$ Polite Termination

---

### 3. Verification & Test Suite Summary

Across the entire codebase, **75 out of 75 automated tests pass with 100% success rate**:

| Test Suite | Purpose | Tests | Status |
|---|---|---|---|
| `test_stage2_fifo_and_question_management.py` | Stage 2 technical questions, FIFO queue, per-question allowances, hints, timeouts | 10 | **PASS** (10/10) |
| `test_skip_revisit_routing.py` | Skip/revisit routing, pause/resume, preference disambiguation, immutability | 12 | **PASS** (12/12) |
| `test_phase1_and_universal_policy.py` | Phase 1 entry, greeting, nervousness, 20s prep timer, universal off-topic | 26 | **PASS** (26/26) |
| `verify_all_guardrails.py` | Deterministic guardrails (G01–G25) | 23 | **PASS** (23/23) |
| `test_additional_scenarios.py` | UC31–UC34 edge cases | 4 | **PASS** (4/4) |
| **Total** | | **75** | **100% PASS** |

---

### 4. LiveKit Real-Time Integration Status
- LiveKit agent worker running continuously in background dev mode (`agent.py dev`).
- Gnani STT (`en-IN`) and TTS (`Nalini`) adapters integrated.
- Silero VAD turn endpointing active with answer timer triggers.
