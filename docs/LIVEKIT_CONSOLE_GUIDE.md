# LiveKit Cloud Agent Console Verification Guide

This guide details how to interactively test and demonstrate VANI 2.0 using the **LiveKit Cloud Agent Console**.

## 1. Prerequisites

1. Your `.env` file in `examples/vani_interview/.env` must contain:
   - `LIVEKIT_URL` (e.g. `wss://vani-2-0-1khnawsy.livekit.cloud`)
   - `LIVEKIT_API_KEY`
   - `LIVEKIT_API_SECRET`
   - `GNANI_API_KEY`
   - `GEMINI_API_KEY`
   - `AGENT_NAME=vani-interviewer`
2. Start the VANI LiveKit worker locally:
   ```powershell
   cd d:\Downloads\agents\examples\vani_interview
   d:\Downloads\agents\.venv\Scripts\python.exe agent.py dev
   ```
3. Look for the startup log:
   `registered worker ... agent_name: vani-interviewer`

## 2. Accessing the LiveKit Cloud Console

1. Navigate to your LiveKit Cloud dashboard: [https://cloud.livekit.io/](https://cloud.livekit.io/)
2. Open your project corresponding to `vani-2-0-1khnawsy`.
3. In the left navigation, click on **Agents** (or **Sandbox / Agent Playground**).
4. Verify that `vani-interviewer` shows as **Active / Online**.
5. Click **Connect** (or launch a test room) with microphone enabled.

## 3. Recommended Spoken Demo Walkthrough

### Phase 1: Onboarding & Skill Selection
1. **Automatic Greeting (UC01)**:
   - *VANI speaks*: "Hello! Welcome to your VANI technical interview. I will be your interviewer today. Are you ready to begin?"
2. **Readiness Confirmation (UC02)**:
   - *You speak*: "Yes, I am ready to begin."
   - *VANI speaks*: "Wonderful! Today's interview consists of three primary technical questions with follow-ups. You can choose from Python, Java, JavaScript, React, SQL, or Docker. Which skill would you like to focus on?"
3. **Skill Selection (UC07)**:
   - *You speak*: "I would like to do Python."
   - *VANI speaks*: "Great, let's begin your Python interview. Question one: Could you explain how decorators work in Python and what problem they solve?"

### Phase 2: Contextual Follow-up
4. **Answer Question 1 (UC13, UC14)**:
   - *You speak*: "A decorator is a function that modifies another function using a wrapper and closure."
5. **Contextual Follow-up (UC18)**:
   - *VANI dynamically evaluates your answer and speaks*: "That's a clear explanation of how they wrap functions. How would you handle functions that accept different numbers of arguments when writing that wrapper?"
6. **Answer Follow-up (UC23)**:
   - *You speak*: "By accepting `*args` and `**kwargs` in the inner wrapper function."
   - *VANI advances to Question 2*: "Thank you for that response. Let's move on to the next topic. Question two: What is the Global Interpreter Lock in CPython...?"

### Phase 3: Conversational Controls
7. **Repeat Question (UC24)**:
   - *You speak*: "Could you please repeat that question?"
   - *VANI speaks*: "Certainly, let me repeat the question: What is the Global Interpreter Lock in CPython...?"
8. **Pause Interview (UC25)**:
   - *You speak*: "Please pause for a minute."
   - *VANI speaks*: "The interview is now paused. Take your time, and just say 'resume' or 'I am back' when you are ready to continue."
9. **Resume Interview (UC26)**:
   - *You speak*: "I am back, let's resume."
   - *VANI speaks*: "Welcome back. Resuming our interview. Our current question was: What is the Global Interpreter Lock in CPython...?"

### Phase 4: Progression to Conclusion
10. Answer Questions 2 and 3.
11. **Conclusion (UC30)**:
    - *VANI speaks*: "That concludes all three questions of your technical interview. Thank you very much for your time and answers today. Have a great day!"
    - In-memory state is automatically cleared.
