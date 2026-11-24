from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field

InterviewStateEnum = Literal[
    "INITIALIZATION",
    "GREETING",
    "READINESS_CHECK",
    "ONBOARDING",
    "SKILL_DISCOVERY",
    "SKILL_SELECTION",
    "ASKING_QUESTION",
    "LISTENING",
    "ANSWER_PROCESSING",
    "CLARIFICATION",
    "FOLLOW_UP",
    "CROSS_QUESTION",
    "REPEAT_QUESTION",
    "SKILL_SWITCH",
    "PAUSED",
    "RESUMING",
    "RECOVERY",
    "NEXT_QUESTION",
    "CONCLUSION",
    "COMPLETED",
]

InterviewIntentEnum = Literal[
    "GREETING",
    "CONFIRM_READY",
    "NOT_READY",
    "ASK_CLARIFICATION",
    "LIST_SKILLS",
    "SELECT_SKILL",
    "CHANGE_SKILL",
    "PROVIDE_ANSWER",
    "SHORT_ANSWER",
    "INCOMPLETE_ANSWER",
    "OFF_TOPIC",
    "REPEAT_QUESTION",
    "PAUSE_INTERVIEW",
    "RESUME_INTERVIEW",
    "END_INTERVIEW",
    "SKIP_REQUEST",
    "UNKNOWN",
]

SkipIntentEnum = Literal["SKIP_REQUEST", "OTHER"]
SkipPreferenceEnum = Literal["SKIP_ENTIRELY", "REVISIT_AFTER_NEXT", "UNCLEAR"]

class SkipIntentDecision(BaseModel):
    intent: SkipIntentEnum = Field(description="Classification of whether candidate wants to skip the question or not.")
    confidence: float = Field(default=1.0, description="Confidence score from 0.0 to 1.0.")
    reasoning: str = Field(default="", description="Brief rationale for the intent classification.")

class SkipPreferenceDecision(BaseModel):
    preference: SkipPreferenceEnum = Field(description="Candidate's skip preference: skip entirely, revisit after next question, or unclear.")
    confidence: float = Field(default=1.0, description="Confidence score from 0.0 to 1.0.")
    reasoning: str = Field(default="", description="Brief rationale for the preference classification.")

class SkillInfo(BaseModel):
    name: str
    description: str
    topics: List[str]
    difficulty_levels: List[str] = ["Junior", "Mid-Level", "Senior"]

class Question(BaseModel):
    id: str
    skill: str
    topic: str
    subtopic: str
    difficulty: str
    question_text: str
    expected_concepts: List[str]
    question_type: Literal["conceptual", "implementation", "scenario", "follow_up", "cross_question"] = "conceptual"

class CandidateAnswer(BaseModel):
    question_id: str
    question_text: str
    answer_text: str
    concepts_identified: List[str] = Field(default_factory=list)
    missing_concepts: List[str] = Field(default_factory=list)
    quality: Literal["comprehensive", "partial", "brief", "incorrect", "off_topic"] = "partial"

class LLMDecision(BaseModel):
    detected_intent: InterviewIntentEnum
    reasoning: str
    response_text: str
    proposed_skill: Optional[str] = None
    concepts_identified: List[str] = Field(default_factory=list)
    missing_concepts: List[str] = Field(default_factory=list)
    needs_follow_up: bool = False
    needs_clarification: bool = False
    needs_elaboration: bool = False
