# VANI 2.0 — Final Live Demonstration Guide

This guide provides everything needed to conduct a repeatable, high-quality demonstration of VANI 2.0 using the **LiveKit Agent Web Console**.

---

## 1. Environment & Pre-Flight Checklist

1. Ensure the `.env` file exists in `examples/vani_interview/.env` with valid credentials:
   - `LIVEKIT_URL=wss://vani-2-0-1khnawsy.livekit.cloud`
   - `LIVEKIT_API_KEY=...`
   - `LIVEKIT_API_SECRET=...`
   - `GNANI_API_KEY=...`
   - `GEMINI_API_KEY=...`
   - `AGENT_NAME=vani-interviewer`
   - `GNANI_STT_LANGUAGE=en-IN`
   - `GNANI_TTS_VOICE=Nalini`
   - `GNANI_TTS_MODEL=timbre-v2.5`
2. Test network connectivity by running the smoke test:
   ```powershell
   d:\Downloads\agents\.venv\Scripts\python.exe d:\Downloads\agents\examples\vani_interview\tests\test_vani_integration.py
   ```

---

## 2. Launching the VANI 2.0 LiveKit Worker

Run the agent worker in development mode:

```powershell
cd d:\Downloads\agents\examples\vani_interview
d:\Downloads\agents\.venv\Scripts\python.exe agent.py dev
```

Watch for the startup confirmation in your console:
```text
INFO: livekit.agents: registered worker ... agent_name: vani-interviewer
```

---

## 3. Connecting through LiveKit Agent Web Console

1. Open Google Chrome and go to: **[https://cloud.livekit.io/](https://cloud.livekit.io/)**
2. Select the project: `vani-2-0-1khnawsy`.
3. In the left navigation, click on **Sandbox** (or **Agents Playground**).
4. Select `vani-interviewer` from the agent dropdown.
5. Click **Connect**.
6. When prompted by the browser, click **Allow** to enable microphone access.
7. **Important**: Use headphones or earphones to prevent audio feedback from candidate speakers triggering false interruptions.

---

## 4. Recommended Demonstration Script & Spoken Turns

### Act I: Onboarding & Skill Selection
- **VANI** (Speaks automatically): *"Hello! Welcome to your VANI technical interview. I will be your interviewer today. Are you ready to begin?"*
- **You**: *"Yes, I am ready to start."*
- **VANI**: *"Wonderful! Today's interview consists of three primary technical questions with follow-ups. You can choose from Python, Java, JavaScript, React, SQL, or Docker. Which skill would you like to focus on?"*
- **You**: *"I would like to do Python."*

---

### Act II: Technical Questioning & Adaptive Follow-Up
- **VANI** (Primary Question 1): *"Great, let's begin your Python interview. Question one: Could you explain how decorators work in Python and what problem they solve?"*
- **You** (Technical answer): *"A decorator is a function that wraps another function to modify its behavior using closures and higher-order functions."*
- **VANI** (Contextual Follow-up 1): *"That is a clear explanation of function closures. How would you handle functions that accept different numbers of arguments when writing that wrapper?"*
- **You** (Follow-up answer): *"You accept `*args` and `**kwargs` in the inner wrapper function and forward them into the decorated function."*

---

### Act III: Conversation Controls Demonstration
- **VANI** (Primary Question 2): *"Thank you for that response. Let's move on to the next topic. Question two: What is the Global Interpreter Lock (GIL) in CPython, and how does it affect CPU-bound versus I/O-bound multithreaded code?"*
- **You** (Testing UC31 - Remaining Questions): *"Before I answer, how many questions remain?"*
- **VANI** (Fast-path response in ~1.4s): *"We have covered 1 of 3 primary questions, leaving 2 primary questions remaining. Follow-ups are asked conditionally based on your answers. Whenever you are ready, please proceed with our current question..."*
- **You** (Testing UC25 - Pause): *"Please pause for a second."*
- **VANI** (Fast-path response): *"The interview is now paused. Take your time, and just say 'resume' or 'I am back' when you are ready to continue."*
- **You** (Testing UC26 - Resume): *"I am back, let's resume."*
- **VANI**: *"Welcome back. Resuming our interview. Our current question was: What is the Global Interpreter Lock in CPython...?"*
- **You** (Testing UC32 - Skip): *"I would like to skip this question please."*
- **VANI**: *"Understood, skipping this question. Question three: How do generators differ from normal functions in Python, and how does the yield keyword manage memory when handling large data streams?"*

---

### Act IV: Question 3 & Conclusion
- **You**: *"Generators use the yield statement to lazily produce values on demand instead of loading everything into memory at once."*
- **VANI**: *"That concludes all three questions of your technical interview. Thank you very much for your time and answers today. Have a great day!"*

---

## 5. Troubleshooting & FAQ

| Symptom | Cause | Solution |
|---|---|---|
| **No audio heard from VANI** | Browser tab muted or default output device incorrect. | Check Chrome tab audio icon; verify speakers in LiveKit Console settings. |
| **VANI interrupts candidate early** | High ambient background noise or microphone echo. | Wear headphones; adjust microphone gain in OS settings. |
| **Worker fails to register** | Expired or incorrect LiveKit Cloud credentials. | Check `.env` for `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET`. |
| **STT fails to transcribe** | Microphone mute switch engaged or sample rate mismatch. | Verify Chrome mic indicator shows active green bar while speaking. |
