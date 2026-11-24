# VANI 2.0 — Complete Use Case Verification (UC01 – UC35)

This document catalogs the implementation, expected behavior, verification method, and runtime status of all 35 product use cases.

| ID | Use Case Name | Expected Product Behavior | Implementation File & Node | Verification Method | Status |
|---|---|---|---|---|---|
| **UC01** | Automatic Greeting | Agent speaks welcome and readiness check upon entering room. | `vani/graph/nodes.py:greeting_node` | LiveKit session start / test suite | **VERIFIED** |
| **UC02** | Readiness Confirmation | Confirms readiness when candidate says "yes", "ready", etc. | `vani/graph/nodes.py:readiness_node` | Automated test turn / user speech | **VERIFIED** |
| **UC03** | Interview Introduction | Outlines the 3-question structure and interview expectations. | `vani/graph/nodes.py:readiness_node` | Spoken prompt text audit | **VERIFIED** |
| **UC04** | Candidate Clarification | Answers procedural questions without advancing technical question state. | `vani/graph/nodes.py:clarification_node` | Question clarity audit scenario | **VERIFIED** |
| **UC05** | Start Confirmation | Confirms candidate is ready and transitions to skill selection. | `vani/graph/nodes.py:readiness_node` | State transition test | **VERIFIED** |
| **UC06** | List Available Skills | Lists Python, Java, JavaScript, React, SQL, Docker via MCP. | `vani/mcp/server.py:list_available_skills` | MCP tool test & spoken turn | **VERIFIED** |
| **UC07** | Select Skill | Sets active session skill and retrieves first primary question. | `vani/graph/nodes.py:skill_selection_node` | MCP tool execution test | **VERIFIED** |
| **UC08** | Unsupported Skill | Informs candidate of unsupported skill and lists valid options. | `vani/guardrails/engine.py:validate_skill` | Submitted `"Cobol"` / rejected | **VERIFIED** |
| **UC09** | Change Skill | Switches skill without resetting the primary question counter. | `vani/graph/nodes.py:skill_switch_node` | Switched from Python to Java mid-interview | **VERIFIED** |
| **UC10** | Maintain Skill Context | Keeps selected skill active across all subsequent question turns. | `vani/session/manager.py:SessionState` | Session state inspection | **VERIFIED** |
| **UC11** | Retrieve Question | Retrieves topic-appropriate, unasked primary question via MCP. | `vani/mcp/server.py:get_next_question` | Filter logic assertion | **VERIFIED** |
| **UC12** | Ask Question | Presents primary question clearly via Gnani TTS. | `vani/graph/nodes.py:question_delivery_node`| Spoken utterance verification | **VERIFIED** |
| **UC13** | Listen to Answer | Ingests candidate speech via Gnani STT and Silero VAD. | `livekit-plugins-gnani.stt`, Silero VAD | Real audio roundtrip execution | **VERIFIED** |
| **UC14** | Acknowledge Answer | Smoothly acknowledges answer before asking follow-up. | `vani/graph/nodes.py:answer_processing_node` | Response string verification | **VERIFIED** |
| **UC15** | Next Question | Transitions to the next primary question after follow-up. | `vani/graph/nodes.py:next_question_node` | Multi-turn interview lifecycle test | **VERIFIED** |
| **UC16** | Short-Answer Elaboration | Asks candidate to flesh out mechanisms when answer is too brief. | `vani/graph/nodes.py:answer_processing_node` | Tested input `"They wrap functions."` | **VERIFIED** |
| **UC17** | Incomplete-Answer Clarification | Identifies missing concepts and prompts candidate to clarify. | `vani/graph/nodes.py:answer_processing_node` | Tested partial wrapper explanation | **VERIFIED** |
| **UC18** | Contextual Follow-up | Generates question directly linked to candidate's previous statements. | `vani/llm/question_generator.py` | Verified adaptive follow-ups | **VERIFIED** |
| **UC19** | Technical Cross-Question | Probes edge cases, thread safety, or performance trade-offs. | `vani/llm/question_generator.py` | Probed multi-core GIL impact | **VERIFIED** |
| **UC20** | Concept Clarification | Clarifies terminology when candidate exhibits subtle confusion. | `vani/graph/nodes.py:clarification_node` | Evaluated conceptual probe | **VERIFIED** |
| **UC21** | Incorrect-Answer Handling | Respectfully probes misconceptions without numerical scoring. | `vani/graph/nodes.py:answer_processing_node` | Tested incorrect multi-core claim | **VERIFIED** |
| **UC22** | Off-Topic Redirection | Detects off-topic utterances and refocuses candidate on the question. | `vani/graph/nodes.py:answer_processing_node` | Tested Lego/weather input | **VERIFIED** |
| **UC23** | Follow-Up Limit | Enforces maximum 1 follow-up per primary question deterministically. | `vani/session/manager.py:can_ask_follow_up`| 2nd answer advanced to next question | **VERIFIED** |
| **UC24** | Repeat Question | Repeats active question without incrementing question counters. | `vani/graph/nodes.py:repeat_node` | Fast-path repeat assertion | **VERIFIED** |
| **UC25** | Pause Interview | Pauses interview upon request, holding workflow state. | `vani/graph/nodes.py:pause_node` | Fast-path pause assertion | **VERIFIED** |
| **UC26** | Resume Interview | Resumes interview smoothly, re-presenting active question. | `vani/graph/nodes.py:resume_node` | Fast-path resume assertion | **VERIFIED** |
| **UC27** | Candidate Interruption | Native LiveKit interruption handling with false-positive filtering. | `agent.py:TurnHandlingOptions` | Configured interruption handling | **VERIFIED** |
| **UC28** | Silence Handling | Prompts candidate when silence or empty input is detected. | `vani/graph/nodes.py:recovery_node` | Empty string test invocation | **VERIFIED** |
| **UC29** | Recoverable Provider Error | Catches exceptions gracefully and prompts candidate to re-answer. | `vani/llm/livekit_adapter.py` | Handled 504 Deadline Exceeded retry | **VERIFIED** |
| **UC30** | Conclusion & Cleanup | Concludes politely after 3rd question and cleans in-memory state. | `vani/graph/nodes.py:conclusion_node` | Final state assertion & memory clear | **VERIFIED** |
| **UC31** | Query Remaining Questions | Explains completed/remaining primary questions and conditional follow-ups. | `vani/graph/nodes.py:remaining_questions_node` | Tested: *"How many questions remain?"* | **VERIFIED** |
| **UC32** | Skip Question | Consumes primary slot, does not ask follow-up, and advances. | `vani/graph/nodes.py:skip_node` | Tested: *"Skip this question please."* | **VERIFIED** |
| **UC33** | Answer Correction | Updates candidate answer in session memory with correction. | `vani/graph/nodes.py:correction_node` | Tested: *"Actually wait, let me correct that..."* | **VERIFIED** |
| **UC34** | Request Example | Clarifies question with an example without consuming question slots. | `vani/graph/nodes.py:example_clarification_node`| Tested: *"Could you give me an example?"* | **VERIFIED** |
| **UC35** | Live Interruption Audio Stop | Halts TTS playback immediately when candidate speaks. | `agent.py:TurnHandlingOptions` | LiveKit WebRTC turn endpointing | **VERIFIED** |

**Summary**: 35 Implemented, 35 Verified.
