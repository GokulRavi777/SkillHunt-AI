"""In-memory data structures, question bank, and session state for VANI MCP server."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any

SUPPORTED_SKILLS: list[str] = [
    "Python",
    "Java",
    "JavaScript",
    "React",
    "SQL",
    "Docker",
]

SUPPORTED_DIFFICULTIES: list[str] = [
    "Beginner",
    "Intermediate",
    "Expert",
]

SKILL_DETAILS: dict[str, dict[str, Any]] = {
    "Python": {
        "description": "High-level programming language emphasizing code readability and simplicity.",
        "topics": [
            "Data types & structures (lists, dicts, tuples, sets)",
            "Object-oriented programming (OOP) and inheritance",
            "Decorators, generators, and iterators",
            "Memory management, GIL, and garbage collection",
            "Asynchronous programming (asyncio, coroutines)",
        ],
    },
    "Java": {
        "description": "Object-oriented, class-based language designed to have few implementation dependencies.",
        "topics": [
            "Core OOP concepts (polymorphism, abstraction, encapsulation)",
            "Java Collections Framework and Generics",
            "Multithreading, concurrency, and Java Memory Model",
            "JVM internals, classloaders, and Garbage Collection",
            "Spring framework and microservices architecture",
        ],
    },
    "JavaScript": {
        "description": "Dynamic scripting language for web pages, asynchronous event-driven applications.",
        "topics": [
            "Scope, closures, hoisting, and prototypes",
            "Event loop, microtasks, macrotasks, and Promises",
            "ES6+ features (destructuring, spread, arrow functions)",
            "DOM manipulation, event delegation, and bubbling",
            "Async/await, error handling, and modules",
        ],
    },
    "React": {
        "description": "Declarative component-based JavaScript library for building user interfaces.",
        "topics": [
            "Component lifecycle and functional components",
            "Hooks (useState, useEffect, useMemo, useCallback, useRef)",
            "Virtual DOM, reconciliation, and diffing algorithm",
            "State management (Context API, Redux, Zustand)",
            "Performance optimization (memoization, lazy loading)",
        ],
    },
    "SQL": {
        "description": "Domain-specific language used in programming and managing relational databases.",
        "topics": [
            "Joins (INNER, LEFT, RIGHT, FULL, CROSS)",
            "Indexes (B-Tree, Hash), query optimization, and EXPLAIN plans",
            "ACID properties and transaction isolation levels",
            "Subqueries, CTEs, and window functions (ROW_NUMBER, RANK)",
            "Database normalization and schema design",
        ],
    },
    "Docker": {
        "description": "Platform for developing, shipping, and running applications in containers.",
        "topics": [
            "Containers vs virtual machines architecture",
            "Dockerfile directives (FROM, RUN, CMD, ENTRYPOINT, COPY)",
            "Docker networking (bridge, host, overlay)",
            "Volumes, bind mounts, and persistent storage",
            "Docker Compose, multi-stage builds, and image optimization",
        ],
    },
}

QUESTION_BANK: list[dict[str, str]] = [
    # Python
    {
        "id": "py_beg_1",
        "skill": "Python",
        "difficulty": "Beginner",
        "question": "What is the key difference between a mutable and an immutable data type in Python, and can you give examples of each?",
    },
    {
        "id": "py_beg_2",
        "skill": "Python",
        "difficulty": "Beginner",
        "question": "How do lists and tuples differ in Python, and when would you choose a tuple over a list?",
    },
    {
        "id": "py_int_1",
        "skill": "Python",
        "difficulty": "Intermediate",
        "question": "How do Python generators work, and how does the 'yield' keyword differ from a standard 'return'?",
    },
    {
        "id": "py_int_2",
        "skill": "Python",
        "difficulty": "Intermediate",
        "question": "What is a Python decorator, and how would you implement a basic timer decorator to measure function execution time?",
    },
    {
        "id": "py_exp_1",
        "skill": "Python",
        "difficulty": "Expert",
        "question": "Can you explain the Global Interpreter Lock (GIL) in CPython and how it impacts CPU-bound versus I/O-bound concurrency?",
    },
    # Java
    {
        "id": "java_beg_1",
        "skill": "Java",
        "difficulty": "Beginner",
        "question": "What is the difference between method overloading and method overriding in Java?",
    },
    {
        "id": "java_int_1",
        "skill": "Java",
        "difficulty": "Intermediate",
        "question": "How does HashMap work internally in Java 8, and how are hash collisions handled?",
    },
    {
        "id": "java_exp_1",
        "skill": "Java",
        "difficulty": "Expert",
        "question": "How does the Java Garbage Collector divide memory into generations, and what happens during a Minor versus Major GC?",
    },
    # JavaScript
    {
        "id": "js_beg_1",
        "skill": "JavaScript",
        "difficulty": "Beginner",
        "question": "What is the difference between '==' and '===' operators in JavaScript?",
    },
    {
        "id": "js_int_1",
        "skill": "JavaScript",
        "difficulty": "Intermediate",
        "question": "Can you explain how closures work in JavaScript and provide a common use case?",
    },
    {
        "id": "js_exp_1",
        "skill": "JavaScript",
        "difficulty": "Expert",
        "question": "How does the JavaScript Event Loop coordinate execution between the call stack, microtask queue, and macrotask queue?",
    },
    # React
    {
        "id": "react_beg_1",
        "skill": "React",
        "difficulty": "Beginner",
        "question": "What is the purpose of state in React, and how does it differ from props?",
    },
    {
        "id": "react_int_1",
        "skill": "React",
        "difficulty": "Intermediate",
        "question": "How does useEffect hook work, and what role does the dependency array play in preventing unnecessary re-renders?",
    },
    {
        "id": "react_exp_1",
        "skill": "React",
        "difficulty": "Expert",
        "question": "Explain the React reconciliation algorithm and how React Fiber helps prioritize rendering updates.",
    },
    # SQL
    {
        "id": "sql_beg_1",
        "skill": "SQL",
        "difficulty": "Beginner",
        "question": "What is the difference between an INNER JOIN and a LEFT JOIN in SQL?",
    },
    {
        "id": "sql_int_1",
        "skill": "SQL",
        "difficulty": "Intermediate",
        "question": "What are database indexes, how do they speed up SELECT queries, and what is their trade-off during writes?",
    },
    {
        "id": "sql_exp_1",
        "skill": "SQL",
        "difficulty": "Expert",
        "question": "Can you explain the difference between the four SQL transaction isolation levels and what read phenomena they prevent?",
    },
    # Docker
    {
        "id": "docker_beg_1",
        "skill": "Docker",
        "difficulty": "Beginner",
        "question": "What is the difference between a Docker image and a Docker container?",
    },
    {
        "id": "docker_int_1",
        "skill": "Docker",
        "difficulty": "Intermediate",
        "question": "What is the difference between the CMD and ENTRYPOINT instructions in a Dockerfile?",
    },
    {
        "id": "docker_exp_1",
        "skill": "Docker",
        "difficulty": "Expert",
        "question": "How do multi-stage builds in Docker work, and how do they reduce production container image size?",
    },
]


class AssessmentStatus(str, Enum):
    INITIALIZING = "INITIALIZING"
    AWAITING_READINESS = "AWAITING_READINESS"
    IN_PROGRESS = "IN_PROGRESS"
    WRAPPING_UP = "WRAPPING_UP"
    COMPLETED = "COMPLETED"
    TERMINATED_EARLY = "TERMINATED_EARLY"


@dataclass
class RecordedResponse:
    skill_name: str
    question: str
    candidate_response: str
    timestamp: float = field(default_factory=time.time)
    persisted: bool = True


@dataclass
class SessionState:
    candidate_id: str | None = None
    room_name: str | None = None
    selected_skill: str | None = "Python"
    selected_difficulty: str = "Beginner"
    status: AssessmentStatus = AssessmentStatus.AWAITING_READINESS
    target_question_count: int = 3
    asked_question_ids: list[str] = field(default_factory=list)
    recorded_responses: list[RecordedResponse] = field(default_factory=list)
    current_question_follow_ups: int = 0
    max_follow_ups_per_question: int = 1
    current_question_repeat_count: int = 0
    max_repeats_per_question: int = 2
    current_question_clarifications: int = 0
    max_clarifications_per_question: int = 1
    last_asked_question_text: str | None = None
    readiness_confirmed: bool = False


class InMemorySessionStore:
    """Manages interview state in memory with strict lifecycle guardrails."""

    def __init__(self) -> None:
        self.state = SessionState()

    def reset(self) -> None:
        self.state = SessionState()

    def bind_session(self, candidate_id: str, room_name: str) -> None:
        """Bind candidate identity and room to session (Guardrail 2)."""
        self.state.candidate_id = candidate_id
        self.state.room_name = room_name

    def confirm_readiness(self) -> bool:
        """Readiness confirmation gate (Guardrail 3)."""
        self.state.readiness_confirmed = True
        self.state.status = AssessmentStatus.IN_PROGRESS
        return True

    def set_skill(self, skill: str, difficulty: str = "Beginner") -> None:
        self.state.selected_skill = skill
        self.state.selected_difficulty = difficulty

    def record_question(self, question_id: str, question_text: str | None = None) -> None:
        if question_id not in self.state.asked_question_ids:
            self.state.asked_question_ids.append(question_id)
        if question_text:
            self.state.last_asked_question_text = question_text
        self.state.current_question_follow_ups = 0
        self.state.current_question_repeat_count = 0
        self.state.current_question_clarifications = 0

    def can_repeat_question(self) -> bool:
        """Repetition and clarification limits (Conversational Guardrail 6)."""
        return self.state.current_question_repeat_count < self.state.max_repeats_per_question

    def record_question_repeat(self) -> bool:
        if not self.can_repeat_question():
            return False
        self.state.current_question_repeat_count += 1
        return True

    def can_clarify_question(self) -> bool:
        """Clarification limits enforcement (Conversational Guardrail 6)."""
        return self.state.current_question_clarifications < self.state.max_clarifications_per_question

    def record_question_clarification(self) -> bool:
        if not self.can_clarify_question():
            return False
        self.state.current_question_clarifications += 1
        return True

    def can_follow_up(self) -> bool:
        """Follow-up quota enforcement (Guardrail 5)."""
        return self.state.current_question_follow_ups < self.state.max_follow_ups_per_question

    def record_follow_up(self) -> bool:
        if not self.can_follow_up():
            return False
        self.state.current_question_follow_ups += 1
        return True

    def record_response(self, skill: str, question: str, response: str) -> RecordedResponse:
        """Record response with persistence confirmation (Guardrail 7)."""
        record = RecordedResponse(
            skill_name=skill,
            question=question,
            candidate_response=response,
            timestamp=time.time(),
            persisted=True,
        )
        self.state.recorded_responses.append(record)
        return record

    def is_question_quota_reached(self) -> bool:
        """Configured question completion enforcement (Guardrail 4)."""
        return len(self.state.recorded_responses) >= self.state.target_question_count

    def can_conclude_assessment(self, candidate_explicit_exit: bool = False) -> tuple[bool, str]:
        """Premature completion prevention (Guardrail 8)."""
        if candidate_explicit_exit:
            self.state.status = AssessmentStatus.TERMINATED_EARLY
            return True, "Candidate requested early termination."
        if self.is_question_quota_reached():
            self.state.status = AssessmentStatus.COMPLETED
            return True, f"Target question count ({self.state.target_question_count}) reached."
        return False, f"Cannot conclude prematurely: only {len(self.state.recorded_responses)} of {self.state.target_question_count} completed."
