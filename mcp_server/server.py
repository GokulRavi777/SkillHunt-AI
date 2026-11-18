"""Official FastMCP server implementing SkillHunt AI technical interview tools and prompt instructions.

All candidate profile data (candidate_name, skill, proficiency) is injected dynamically
from the verified resume setup. No hardcoded skills, lists, or static assumptions.
"""

from __future__ import annotations

import argparse
from typing import Any

from mcp.server.fastmcp import FastMCP

try:
    from .data import (
        QUESTION_BANK,
        SUPPORTED_DIFFICULTIES,
        InMemorySessionStore,
    )
except ImportError:
    from data import (
        QUESTION_BANK,
        SUPPORTED_DIFFICULTIES,
        InMemorySessionStore,
    )

# Shared in-memory session store
session_store = InMemorySessionStore()

# Initialize FastMCP Server
mcp = FastMCP("skillhunt-interview-mcp")


def build_main_system_prompt(
    candidate_name: str,
    skill: str,
    proficiency: str,
) -> str:
    """Immutable base system prompt used consistently on every LLM call."""
    return f"""You are SkillHunt AI, a professional, articulate, and natural AI technical voice interviewer conducting an oral assessment over real-time voice.

CANDIDATE SESSION PROFILE:
- Candidate Name: {candidate_name}
- Assessment Skill: {skill}
- Proficiency Level: {proficiency}
(Note: This profile is pre-configured from the candidate's verified resume. Do not ask them to choose or change their skill or level. Focus all questions on {skill} calibrated for {proficiency} complexity.)

CORE VOICE RULES:
1. You are speaking aloud through text-to-speech. Keep every turn concise, conversational, and direct (1 to 3 spoken sentences, strictly under 40 words).
2. Never output markdown formatting (no asterisks, bolding, bullet points, numbered lists, or code blocks) as these will be read aloud literally.
3. Maintain a calm, respectful, objective, and professional tone. Avoid exaggerated praise or filler chatter.

GLOBAL GUARDRAILS:
1. Strict English Enforcement:
   - If the candidate speaks in Hindi, Tamil, Telugu, Hinglish, or any language other than English, respond strictly with:
     "I can't understand. Please continue the conversation in English."
2. 20-Second Hold Policy (Single-Use Quota):
   - Candidates are entitled to a single pause of up to 20 seconds.
   - If requested a second time, politely refuse: "You have already used your 20-second pause quota. We cannot pause again. Would you like to proceed with the interview now, or take it after some time?"
3. Interview Boundary & Flow Policy:
   - If the candidate asks about the interview flow, format, syllabus, or topics to be asked, respond strictly with:
     "The rules, interview structure, and topics were already provided during your lobby briefing. Please let me know when you are ready to begin."
4. Neutral Technical Assessment:
   - Acknowledge responses neutrally (e.g. "Understood", "Got it", "Thank you for explaining that").
   - Politely decline and redirect off-topic, personal, or inappropriate queries.
"""


def _normalize_skill(skill_name: str) -> str:
    """Accept and normalize any technical skill injected from candidate's resume."""
    if not skill_name or not skill_name.strip():
        raise ValueError("Skill name cannot be empty.")
    return skill_name.strip()


def _normalize_difficulty(difficulty: str) -> str:
    """Normalize difficulty level dynamically."""
    if not difficulty or not difficulty.strip():
        return "Intermediate"
    cleaned = difficulty.strip().title()
    for supported in SUPPORTED_DIFFICULTIES:
        if supported.lower() == cleaned.lower():
            return supported
    raise ValueError(f"Unsupported difficulty: '{difficulty}'. Supported: {SUPPORTED_DIFFICULTIES}")


FEW_SHOT_QUESTION_TEMPLATES: dict[str, list[dict[str, str]]] = {
    "Beginner": [
        {
            "topic": "Fundamentals & Memory Model",
            "template": "In {skill}, could you explain the fundamental difference between stack memory and heap memory allocation?",
            "follow_up": "When would allocating on the stack be preferred over the heap?",
        },
        {
            "topic": "Syntax & Core Structures",
            "template": "What is the role of classes, constructors, and destructors in {skill}, and when are resources automatically cleaned up?",
            "follow_up": "Why should destructors or cleanup methods handle errors gracefully?",
        },
        {
            "topic": "Standard Collections & Operations",
            "template": "How do standard container collections or arrays in {skill} manage dynamic capacity and lookups under the hood?",
            "follow_up": "What is the time complexity difference between indexed lookup and searching in an unordered collection?",
        },
    ],
    "Intermediate": [
        {
            "topic": "Resource Lifecycles & RAII",
            "template": "In {skill}, how do smart pointers or scoped references ensure deterministic resource cleanup under the RAII idiom?",
            "follow_up": "How do you prevent circular reference memory leaks in reference-counted structures?",
        },
        {
            "topic": "Error Boundaries & Exceptions",
            "template": "Can you explain how exception handling and resource cleanup interact in {skill}, and what guarantees are needed to avoid resource leaks?",
            "follow_up": "What is the difference between basic and strong exception safety guarantees?",
        },
        {
            "topic": "Move Semantics & Performance",
            "template": "How do move semantics, references, or zero-copy patterns in {skill} eliminate redundant copy overhead in performance-critical code?",
            "follow_up": "When does the compiler apply copy elision or return value optimization automatically?",
        },
    ],
    "Expert": [
        {
            "topic": "Lock-Free Concurrency & Memory Model",
            "template": "Under the {skill} concurrency model, how do atomic operations and memory ordering constraints prevent data races in lock-free architectures?",
            "follow_up": "How do you avoid false sharing and cache-line bouncing in high-throughput multi-core workloads?",
        },
        {
            "topic": "Runtime Internals & Metaprogramming",
            "template": "How does the {skill} runtime or compiler implement virtual method lookup tables, and what is the exact memory and cache overhead?",
            "follow_up": "How do modern optimizing compilers perform devirtualization?",
        },
        {
            "topic": "System Architecture & Resilience",
            "template": "In high-throughput distributed systems using {skill}, how do you diagnose event-loop or thread starvation under sudden load spikes?",
            "follow_up": "What telemetry and bounded queue patterns do you implement to enforce latency SLAs?",
        },
    ],
}


@mcp.tool()
def get_state_instruction(
    state: str,
    candidate_name: str = "",
    skill: str = "",
    proficiency: str = "",
    question: str = "",
    repeat_count: int = 0,
) -> dict[str, Any]:
    """Fetch state-specific instructions and guardrails dynamically from the MCP server.

    Args:
        state: The interview lifecycle state (greeting, readiness_gate, flow_boundary,
               hold_20s_start, hold_20s_expired, hold_exhausted, question_turn,
               elaboration_request, repeat_question, follow_up, no_coaching, completed).
        candidate_name: Injected candidate name.
        skill: Injected technical skill.
        proficiency: Injected proficiency level.
        question: Active question text (if in question state).
        repeat_count: Current repeat count for active question.

    Returns:
        dict: The state-specific instruction and applicable guardrails.
    """
    normalized_state = state.strip().lower()

    if normalized_state == "greeting":
        instruction = (
            f"Your current turn is strictly the opening greeting. Warmly greet {candidate_name} by name, "
            f"introduce yourself as SkillHunt AI, announce the interview is on {skill} at the {proficiency} level, "
            f"and ask: 'Are you ready to begin?' Do NOT ask any technical questions."
        )
    elif normalized_state == "readiness_gate":
        instruction = (
            f"The candidate has not yet confirmed readiness. You can ONLY transition to Question 1 if they confirm readiness "
            f"(e.g. 'yes', 'ready', 'let's begin'). If the candidate asks about the interview flow, rules, or topics, state: "
            f"'The rules, interview structure, and topics were already provided during your lobby briefing. Please let me know when you are ready to begin.' "
            f"If candidate asks to hold and hold is unused, allow a 20-second hold. If hold was already used, inform them wait breaks are allowed only once."
        )
    elif normalized_state == "flow_boundary":
        instruction = (
            "The candidate asked about the interview flow, rules, or topics. Respond strictly with: "
            "'The rules, interview structure, and topics were already provided during your lobby briefing. Please let me know when you are ready to begin.'"
        )
    elif normalized_state == "hold_20s_start":
        instruction = (
            "The candidate requested to hold (single-use quota). Agree warmly: "
            "'Sure, take your time! I will hold on for 20 seconds. Let me know when you're ready.'"
        )
    elif normalized_state == "hold_20s_expired":
        instruction = (
            "The 20-second hold timer has expired. Prompt the candidate: "
            "'Twenty seconds have passed. We can continue the interview now, or if you need more time, you can take the interview after some time.'"
        )
    elif normalized_state == "hold_exhausted":
        instruction = (
            "The candidate requested to hold again, but the 1-time hold quota is exhausted. Firmly respond: "
            "'You have already used your 20-second pause quota. We cannot pause again. Would you like to proceed with the interview now, or take it after some time?'"
        )
    elif normalized_state == "elaboration_request":
        instruction = (
            "The candidate's response was too brief or vague (< 5 words). You are permitted to ask for elaboration only once per question: "
            "'Could you elaborate on how that works in practice?'"
        )
    elif normalized_state == "repeat_question":
        if repeat_count >= 2:
            instruction = (
                "The candidate asked to repeat, but the 2-repeat limit is reached. Respond: "
                "'I have already repeated the question twice. Please provide your best answer based on what you heard.'"
            )
        else:
            instruction = f"The candidate asked to repeat. Repeat the question clearly: 'Certainly. The question is: {question}'"
    elif normalized_state == "no_coaching":
        instruction = (
            "The candidate asked for the answer, a hint, or to be coached. Refuse firmly: "
            "'I cannot provide the solution or hints during the evaluation. Please share what you know, or we can move on.'"
        )
    elif normalized_state == "follow_up":
        instruction = (
            f"This is the single global follow-up permitted for the entire interview. Ask 1 concise technical follow-up "
            f"directly probing the candidate's answer to '{question}'. Keep it under 30 words."
        )
    elif normalized_state == "question_turn":
        instruction = (
            f"Active question is '{question}'. Assess the candidate's answer neutrally without coaching or revealing the solution. "
            f"If incomplete, ask 1 follow-up within quota. If complete, acknowledge neutrally and call save_interview_response before retrieving the next question."
        )
    elif normalized_state == "completed":
        instruction = (
            f"All 3 questions have been completed. Thank {candidate_name}, confirm responses are recorded in the session database, "
            f"and deliver a warm, polite closing statement."
        )
    else:
        instruction = f"Proceed with standard technical interview evaluation for {skill} ({proficiency})."

    return {
        "status": "success",
        "state": normalized_state,
        "instruction": instruction,
    }


@mcp.tool()
def generate_few_shot_question(
    skill: str,
    proficiency: str = "Intermediate",
    question_index: int = 0,
) -> dict[str, Any]:
    """Generate a dynamically calibrated question using few-shot exemplars for any skill and proficiency."""
    canonical_skill = _normalize_skill(skill)
    canonical_diff = _normalize_difficulty(proficiency)

    exemplars = FEW_SHOT_QUESTION_TEMPLATES.get(canonical_diff, FEW_SHOT_QUESTION_TEMPLATES["Intermediate"])
    idx = question_index % len(exemplars)
    template_data = exemplars[idx]

    question_text = template_data["template"].format(skill=canonical_skill)
    follow_up_text = template_data["follow_up"].format(skill=canonical_skill)
    topic = template_data["topic"].format(skill=canonical_skill)
    q_id = f"{canonical_skill.lower()}_{canonical_diff.lower()}_{question_index + 1}"

    return {
        "status": "success",
        "question_id": q_id,
        "skill": canonical_skill,
        "difficulty": canonical_diff,
        "topic": topic,
        "question": question_text,
        "suggested_follow_up": follow_up_text,
    }


@mcp.prompt()
def main_system_prompt(
    candidate_name: str,
    skill: str,
    proficiency: str,
) -> str:
    """MCP Prompt exposing the constant main system prompt."""
    return build_main_system_prompt(candidate_name, skill, proficiency)


@mcp.tool()
def select_interview_skill(skill_name: str, difficulty: str = "Intermediate") -> dict[str, Any]:
    """Configure the candidate's chosen skill and interview difficulty level."""
    canonical_skill = _normalize_skill(skill_name)
    canonical_diff = _normalize_difficulty(difficulty)

    session_store.set_skill(canonical_skill, canonical_diff)
    return {
        "status": "success",
        "selected_skill": canonical_skill,
        "difficulty": canonical_diff,
        "message": f"Interview skill set to {canonical_skill} at {canonical_diff} difficulty.",
    }


@mcp.tool()
def get_next_question(
    skill_name: str,
    difficulty: str = "Intermediate",
    previous_question_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Retrieve an appropriate interview question for the injected skill and difficulty."""
    canonical_skill = _normalize_skill(skill_name)
    canonical_diff = _normalize_difficulty(difficulty)

    excluded_ids = set(previous_question_ids or [])
    excluded_ids.update(session_store.state.asked_question_ids)

    # Check question bank if available
    candidates = [
        q
        for q in QUESTION_BANK
        if q["skill"].lower() == canonical_skill.lower() and q["difficulty"].lower() == canonical_diff.lower()
    ]

    available = [q for q in candidates if q["id"] not in excluded_ids]
    if available:
        selected = available[0]
    elif candidates:
        selected = candidates[0]
    else:
        # Dynamic few-shot question calibrated for injected skill & level
        q_idx = len(session_store.state.asked_question_ids)
        few_shot = generate_few_shot_question(canonical_skill, canonical_diff, q_idx)
        selected = {
            "id": few_shot["question_id"],
            "skill": few_shot["skill"],
            "difficulty": few_shot["difficulty"],
            "question": few_shot["question"],
        }

    session_store.record_question(selected["id"], selected["question"])
    return {
        "status": "success",
        "question_id": selected["id"],
        "skill": selected["skill"],
        "difficulty": selected["difficulty"],
        "question": selected["question"],
    }


@mcp.tool()
def repeat_active_question() -> dict[str, Any]:
    """Repeat the active question without fetching a new one (max 2 repeats limit)."""
    if not session_store.state.asked_question_ids or not session_store.state.last_asked_question_text:
        return {"status": "error", "message": "No active question to repeat."}

    if not session_store.can_repeat_question():
        return {
            "status": "limit_reached",
            "message": "Maximum repetition limit (2) reached for this question. Candidate must provide their answer.",
            "repeat_count": session_store.state.current_question_repeat_count,
            "max_repeats": session_store.state.max_repeats_per_question,
            "question": session_store.state.last_asked_question_text,
        }

    session_store.record_question_repeat()
    return {
        "status": "success",
        "question": session_store.state.last_asked_question_text,
        "repeat_count": session_store.state.current_question_repeat_count,
        "max_repeats": session_store.state.max_repeats_per_question,
    }


@mcp.tool()
def save_interview_response(
    skill_name: str,
    question: str,
    candidate_response: str,
) -> dict[str, Any]:
    """Store the candidate's answer for the current question in the in-memory session."""
    canonical_skill = _normalize_skill(skill_name)
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")
    if not candidate_response or not candidate_response.strip():
        raise ValueError("Candidate response cannot be empty.")

    record = session_store.record_response(
        skill=canonical_skill,
        question=question.strip(),
        response=candidate_response.strip(),
    )

    quota_reached = session_store.is_question_quota_reached()

    return {
        "status": "success",
        "persisted": record.persisted,
        "message": f"Candidate response recorded for {canonical_skill}.",
        "total_recorded": len(session_store.state.recorded_responses),
        "target_questions": session_store.state.target_question_count,
        "quota_reached": quota_reached,
    }


@mcp.tool()
def get_assessment_status() -> dict[str, Any]:
    """Retrieve current lifecycle state, questions completed, and termination readiness."""
    state = session_store.state
    can_conclude, reason = session_store.can_conclude_assessment()
    return {
        "status": state.status.value,
        "selected_skill": state.selected_skill,
        "selected_difficulty": state.selected_difficulty,
        "readiness_confirmed": state.readiness_confirmed,
        "completed_questions": len(state.recorded_responses),
        "target_questions": state.target_question_count,
        "quota_reached": session_store.is_question_quota_reached(),
        "can_conclude": can_conclude,
        "lifecycle_message": reason,
    }


def main() -> None:
    """Run the MCP server from command-line."""
    parser = argparse.ArgumentParser(description="SkillHunt AI Technical Interview MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol (stdio or sse)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for SSE server")
    parser.add_argument("--port", type=int, default=8000, help="Port for SSE server")
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
