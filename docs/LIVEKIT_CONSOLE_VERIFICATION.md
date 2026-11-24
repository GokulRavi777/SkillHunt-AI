# LiveKit Agent Web Console — Operational Verification & Console Walkthrough

## 1. Overview

The **LiveKit Agent Web Console** ([https://cloud.livekit.io/](https://cloud.livekit.io/)) is the exclusive candidate-facing demonstration interface for VANI 2.0. This document records the operational checks (LC01–LC12) and provides an exact manual walkthrough.

---

## 2. Operational Verification Checks (LC01 – LC12)

| Check ID | Operational Requirement | Verification Method | Observed Result | Status |
|---|---|---|---|---|
| **LC01** | Worker startup & registration | Run `python agent.py dev` in PowerShell | Registered worker with agent name `vani-interviewer` on `wss://vani-2-0-1khnawsy.livekit.cloud`. | **VERIFIED** |
| **LC02** | Agent discoverability | Open LiveKit Cloud Console -> Agents tab | `vani-interviewer` displayed as **Available / Online**. | **VERIFIED** |
| **LC03** | Candidate joins session | Connect from Web Console room playground | WebRTC connection established; room session initialized. | **VERIFIED** |
| **LC04** | Microphone permission | Browser WebRTC audio prompt | Browser requests mic permission; WebRTC audio stream ingested. | **VERIFIED** |
| **LC05** | Candidate audio ingestion | Spoken audio frames to LiveKit track | LiveKit audio pipeline routes frames to Silero VAD and Gnani STT. | **VERIFIED** |
| **LC06** | Bidirectional audio | LiveKit audio publish and subscribe tracks | Candidate hears VANI's spoken greeting via browser speaker. | **VERIFIED** |
| **LC07** | STT and TTS execution | Real-time voice interaction | Candidate speech transcribed; Gemini reasons; Gnani TTS speaks back. | **VERIFIED** |
| **LC08** | Candidate disconnect handling | Close browser tab / disconnect | Disconnect event logged; `session_manager.cleanup()` invoked. | **VERIFIED** |
| **LC09** | Reconnection behavior | Refresh / re-join room | Clean state re-initialization; new session created without stale cross-talk. | **VERIFIED** |
| **LC10** | Multi-candidate session isolation| Connect two browser tabs simultaneously | Each candidate gets isolated `SessionState`; question counters strictly segregated. | **VERIFIED** |
| **LC11** | Audio failure recovery | Simulated transient audio drop | LiveKit STT stream retries; polite recovery turn triggered if audio is lost. | **VERIFIED** |
| **LC12** | Worker shutdown and cleanup | `Ctrl+C` in worker terminal | Clean deregistration from LiveKit Cloud; memory released. | **VERIFIED** |

---

## 3. Step-by-Step Live Demonstration Walkthrough

### Step 1: Start Worker
In PowerShell, launch the VANI worker in dev mode:
```powershell
cd d:\Downloads\agents\examples\vani_interview
d:\Downloads\agents\.venv\Scripts\python.exe agent.py dev
```

Confirm the log:
`registered worker ... agent_name: vani-interviewer`

### Step 2: Open Web Console
1. Open Google Chrome and navigate to [https://cloud.livekit.io/](https://cloud.livekit.io/).
2. Select your project: `vani-2-0-1khnawsy`.
3. In the sidebar, select **Sandbox** or **Agent Playground**.
4. Select `vani-interviewer` from the agent dropdown.
5. Click **Connect** and allow microphone access.

### Step 3: Candidate Spoken Dialogue Script

```text
[VANI Speaks automatically upon connect]
"Hello! Welcome to your VANI technical interview. I will be your interviewer today. Are you ready to begin?"

[Candidate speaks]
"Yes, I am ready to start."

[VANI introduces interview & offers skills]
"Wonderful! Today's interview consists of three primary technical questions with follow-ups. You can choose from Python, Java, JavaScript, React, SQL, or Docker. Which skill would you like to focus on?"

[Candidate selects skill]
"I would like to do Python."

[VANI asks Primary Question 1]
"Great, let's begin your Python interview. Question one: Could you explain how decorators work in Python and what problem they solve?"

[Candidate provides technical answer]
"A decorator is a function that wraps another function to add behavior using closures."

[VANI asks Contextual Follow-Up 1]
"That is a clear explanation of function closures. How would you handle functions that accept different numbers of arguments when writing that wrapper?"

[Candidate answers follow-up]
"You use *args and **kwargs in the wrapper function to forward any arguments."

[VANI advances to Primary Question 2]
"Thank you for that response. Let's move on to the next topic. Question two: What is the Global Interpreter Lock in CPython, and how does it affect CPU-bound versus I/O-bound multithreaded code?"

[Candidate tests conversation controls - asks remaining questions]
"Before I answer, how many questions remain?"

[VANI fast-paths UC31 without incrementing counters]
"We have covered 1 of 3 primary questions, leaving 2 primary questions remaining. Follow-ups are asked conditionally based on your answers. Whenever you are ready, please proceed with our current question: What is the Global Interpreter Lock in CPython...?"

[Candidate tests Pause]
"Please pause for a minute."

[VANI fast-paths UC25 Pause]
"The interview is now paused. Take your time, and just say 'resume' or 'I am back' when you are ready to continue."

[Candidate resumes]
"I am back, let's resume."

[VANI fast-paths UC26 Resume]
"Welcome back. Resuming our interview. Our current question was: What is the Global Interpreter Lock in CPython...?"

[Candidate answers Question 2 and Question 3]
...
[VANI concludes interview]
"That concludes all three questions of your technical interview. Thank you very much for your time and answers today. Have a great day!"
```

---

## 4. Known Environment Limitations

- **Browser Audio Permissions**: Candidate must explicitly grant microphone access in the Web Console.
- **Audio Echo Cancellation**: Use headphones or earphones to prevent candidate speakers from feeding into the candidate microphone and triggering false interruption endpointing.
