import json
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP
from vani.schemas.models import SkillInfo, Question
from vani.session.manager import session_manager
from config.settings import settings

# In-memory curated skills repository
SKILLS_CATALOG: Dict[str, SkillInfo] = {
    "Python": SkillInfo(
        name="Python",
        description="Core Python fundamentals for beginners: basic data types, lists, tuples, dictionaries, functions, and control flow.",
        topics=["Data Structures & Mutability", "Dictionaries & Hash Maps", "Functions & Scope", "Control Flow & Error Handling"],
        difficulty_levels=["Beginner"]
    ),
    "Java": SkillInfo(
        name="Java",
        description="Core Java, JVM internals, multithreading, OOP concepts, collections, and Spring framework.",
        topics=["OOP & Interfaces", "JVM & Garbage Collection", "Multithreading & Concurrency", "Collections Framework"],
        difficulty_levels=["Junior", "Mid-Level", "Senior"]
    ),
    "JavaScript": SkillInfo(
        name="JavaScript",
        description="Modern ECMAScript, Event Loop, asynchronous programming, closures, prototypes, and DOM.",
        topics=["Event Loop & Microtasks", "Closures & Scope", "Promises & Async/Await", "Prototypes & Inheritance"],
        difficulty_levels=["Junior", "Mid-Level", "Senior"]
    ),
    "React": SkillInfo(
        name="React",
        description="React component lifecycle, Hooks, state management, reconciliation, and performance optimization.",
        topics=["Hooks & Lifecycle", "Virtual DOM & Reconciliation", "State Management & Context", "Performance Optimization"],
        difficulty_levels=["Junior", "Mid-Level", "Senior"]
    ),
    "SQL": SkillInfo(
        name="SQL",
        description="Relational database queries, indexing, query optimization, ACID transactions, and normalization.",
        topics=["Joins & Subqueries", "Indexing & Execution Plans", "ACID & Transactions", "Schema Design & Normalization"],
        difficulty_levels=["Junior", "Mid-Level", "Senior"]
    ),
    "Docker": SkillInfo(
        name="Docker",
        description="Containerization principles, Dockerfile best practices, networking, volumes, and multi-stage builds.",
        topics=["Container Architecture", "Dockerfile Optimization", "Docker Networking", "Storage & Volumes"],
        difficulty_levels=["Junior", "Mid-Level", "Senior"]
    ),
}

# Curated Primary Technical Questions
QUESTIONS_CATALOG: List[Question] = [
    # Python Questions for Beginners
    Question(
        id="py_q1",
        skill="Python",
        topic="Data Structures & Mutability",
        subtopic="Lists vs Tuples",
        difficulty="Beginner",
        question_text="Could you explain the main differences between a list and a tuple in Python, and give an example of when you would use each?",
        expected_concepts=["mutable vs immutable", "syntax brackets vs parentheses", "modifying or appending elements", "hashable or dictionary keys", "data integrity"],
        question_type="conceptual"
    ),
    Question(
        id="py_q2",
        skill="Python",
        topic="Dictionaries & Hash Maps",
        subtopic="Key-Value Storage & Lookup",
        difficulty="Beginner",
        question_text="How do dictionaries work in Python, and why is looking up a value by its key generally faster than searching through a list?",
        expected_concepts=["key-value pairs", "hash table or hashing", "constant time O(1) lookup", "unique keys", "immutable keys"],
        question_type="conceptual"
    ),
    Question(
        id="py_q3",
        skill="Python",
        topic="Functions & Scope",
        subtopic="Defining Functions & Return vs Print",
        difficulty="Beginner",
        question_text="How do you define a function in Python, and what is the difference between returning a value with return versus printing it with print?",
        expected_concepts=["def keyword", "return passes value back to caller", "print outputs to console", "default None return value", "reusability in expressions"],
        question_type="conceptual"
    ),
    Question(
        id="py_q4",
        skill="Python",
        topic="Control Flow & Error Handling",
        subtopic="Try-Except Blocks",
        difficulty="Beginner",
        question_text="What is the purpose of try and except blocks in Python, and how do they help prevent a program from crashing when an error occurs?",
        expected_concepts=["exception handling", "preventing crashes", "try block executes risky code", "except block catches specific error", "graceful error recovery"],
        question_type="conceptual"
    ),

    # Java Questions
    Question(
        id="java_q1",
        skill="Java",
        topic="JVM & Garbage Collection",
        subtopic="Memory Areas & GC",
        difficulty="Mid-Level",
        question_text="How does memory management work in the JVM, specifically the distinction between Heap and Stack memory?",
        expected_concepts=["Heap for objects", "Stack for frames and primitives", "Garbage collector", "OutOfMemoryError vs StackOverflowError"],
        question_type="conceptual"
    ),
    Question(
        id="java_q2",
        skill="Java",
        topic="Multithreading & Concurrency",
        subtopic="Synchronization & Locks",
        difficulty="Senior",
        question_text="What is the difference between using the synchronized keyword and using ReentrantLock in Java for concurrent thread safety?",
        expected_concepts=["fairness policy", "tryLock timeout", "intrinsic locks", "Condition variables", "lock interruptibility"],
        question_type="implementation"
    ),
    Question(
        id="java_q3",
        skill="Java",
        topic="Collections Framework",
        subtopic="HashMap Internals",
        difficulty="Mid-Level",
        question_text="Can you describe the internal mechanics of a HashMap in Java, including how collisions are resolved in modern Java versions?",
        expected_concepts=["hash code", "bucket array", "linked list to red-black tree", "load factor", "rehash"],
        question_type="conceptual"
    ),

    # JavaScript Questions
    Question(
        id="js_q1",
        skill="JavaScript",
        topic="Event Loop & Microtasks",
        subtopic="Call Stack & Task Queues",
        difficulty="Mid-Level",
        question_text="Can you explain the JavaScript Event Loop, and the exact execution priority between the Call Stack, Microtask queue, and Macrotask queue?",
        expected_concepts=["Call stack", "Microtasks (Promises/queueMicrotask)", "Macrotasks (setTimeout/I/O)", "single-threaded non-blocking"],
        question_type="conceptual"
    ),
    Question(
        id="js_q2",
        skill="JavaScript",
        topic="Closures & Scope",
        subtopic="Lexical Scoping",
        difficulty="Mid-Level",
        question_text="What is a closure in JavaScript, and what is an example of where closures are used or could cause memory retention issues?",
        expected_concepts=["lexical scope", "outer function scope preservation", "private variables", "memory leak potential"],
        question_type="conceptual"
    ),
    Question(
        id="js_q3",
        skill="JavaScript",
        topic="Promises & Async/Await",
        subtopic="Async Error Handling",
        difficulty="Senior",
        question_text="How does async/await under the hood compile down with Promises and Generators, and how should concurrent unhandled rejections be caught?",
        expected_concepts=["syntactic sugar over Promises", "Promise.all vs Promise.allSettled", "try-catch wrapping", "generator coroutine pattern"],
        question_type="implementation"
    ),

    # React Questions
    Question(
        id="react_q1",
        skill="React",
        topic="Virtual DOM & Reconciliation",
        subtopic="Fiber Architecture & Diffing",
        difficulty="Mid-Level",
        question_text="How does React's Virtual DOM diffing algorithm work, and why is the key prop critical when rendering lists?",
        expected_concepts=["heuristic diffing", "component tree comparison", "key for element stability", "minimizing DOM operations"],
        question_type="conceptual"
    ),
    Question(
        id="react_q2",
        skill="React",
        topic="Hooks & Lifecycle",
        subtopic="useEffect & Dependency Arrays",
        difficulty="Mid-Level",
        question_text="In React, how does the useEffect hook handle cleanups, and what problems arise when dependencies are improperly omitted?",
        expected_concepts=["cleanup callback", "stale closures", "infinite re-renders", "referential equality"],
        question_type="implementation"
    ),
    Question(
        id="react_q3",
        skill="React",
        topic="Performance Optimization",
        subtopic="Memoization Hooks",
        difficulty="Senior",
        question_text="When should you use useMemo and useCallback in React, and when might overusing them actually hurt performance?",
        expected_concepts=["referential stability of functions", "expensive calculations", "memoization overhead", "shallow comparison in React.memo"],
        question_type="scenario"
    ),

    # SQL Questions
    Question(
        id="sql_q1",
        skill="SQL",
        topic="Indexing & Execution Plans",
        subtopic="B-Tree Indexes",
        difficulty="Mid-Level",
        question_text="How do B-tree indexes speed up SQL SELECT queries, and what is the trade-off when performing high-volume INSERT or UPDATE operations?",
        expected_concepts=["binary tree traversal", "logarithmic lookup", "index maintenance overhead on writes", "composite index order"],
        question_type="conceptual"
    ),
    Question(
        id="sql_q2",
        skill="SQL",
        topic="ACID & Transactions",
        subtopic="Isolation Levels",
        difficulty="Senior",
        question_text="What are the four standard ACID transaction isolation levels, and what read phenomena (like dirty reads or phantom reads) does each prevent?",
        expected_concepts=["Read Uncommitted", "Read Committed", "Repeatable Read", "Serializable", "dirty reads", "phantom reads"],
        question_type="conceptual"
    ),
    Question(
        id="sql_q3",
        skill="SQL",
        topic="Joins & Subqueries",
        subtopic="JOIN Performance",
        difficulty="Mid-Level",
        question_text="What is the difference between an INNER JOIN, a LEFT OUTER JOIN, and a CROSS JOIN, and when should you prefer a JOIN over a correlated subquery?",
        expected_concepts=["matching records", "null preservation in outer join", "cartesian product in cross join", "query optimizer plan"],
        question_type="implementation"
    ),

    # Docker Questions
    Question(
        id="docker_q1",
        skill="Docker",
        topic="Container Architecture",
        subtopic="Namespaces & Cgroups",
        difficulty="Senior",
        question_text="How does Docker achieve isolation on Linux using namespaces and cgroups, and how does this fundamentally differ from a Virtual Machine hypervisor?",
        expected_concepts=["Linux namespaces for process/network isolation", "cgroups for resource limits", "shared host kernel", "lightweight vs guest OS"],
        question_type="conceptual"
    ),
    Question(
        id="docker_q2",
        skill="Docker",
        topic="Dockerfile Optimization",
        subtopic="Multi-Stage Builds & Layer Caching",
        difficulty="Mid-Level",
        question_text="How do multi-stage Docker builds reduce container image size and improve security for production deployments?",
        expected_concepts=["separate build and runtime stages", "excluding compilers and build tools", "layer caching optimization", "minimal final base image"],
        question_type="implementation"
    ),
    Question(
        id="docker_q3",
        skill="Docker",
        topic="Storage & Volumes",
        subtopic="Volumes vs Bind Mounts",
        difficulty="Mid-Level",
        question_text="What is the key difference between Docker named volumes and host bind mounts, and which one is recommended for persistent database storage?",
        expected_concepts=["Docker managed /var/lib/docker", "host filesystem coupling", "named volumes for databases", "portability and permissions"],
        question_type="conceptual"
    ),
]

# FastMCP Server Instance
mcp_server = FastMCP("Vani Interview MCP Server")

@mcp_server.tool()
def list_available_skills() -> Dict[str, Any]:
    """Returns the list of supported technical skills with descriptions."""
    skills = [
        {"name": s.name, "description": s.description, "topics": s.topics}
        for s in SKILLS_CATALOG.values()
    ]
    return {
        "status": "success",
        "count": len(skills),
        "skills": skills
    }

@mcp_server.tool()
def get_skill_details(skill: str) -> Dict[str, Any]:
    """Returns details, topics, and difficulty levels for a specific technical skill.
    
    Args:
        skill: Name of the technical skill (e.g., Python, Java, React).
    """
    skill_clean = skill.strip()
    matched = next((k for k in SKILLS_CATALOG if k.lower() == skill_clean.lower()), None)
    if not matched:
        return {
            "status": "error",
            "message": f"Skill '{skill}' is not supported. Supported skills are: {', '.join(SKILLS_CATALOG.keys())}"
        }
    info = SKILLS_CATALOG[matched]
    return {
        "status": "success",
        "skill": info.name,
        "description": info.description,
        "topics": info.topics,
        "difficulty_levels": info.difficulty_levels
    }

@mcp_server.tool()
def select_interview_skill(session_id: str, skill: str) -> Dict[str, Any]:
    """Sets or switches the active technical interview skill for the current session.
    
    Args:
        session_id: Active session identifier.
        skill: Selected technical skill name.
    """
    skill_clean = skill.strip()
    matched = next((k for k in SKILLS_CATALOG if k.lower() == skill_clean.lower()), None)
    if not matched:
        return {
            "status": "error",
            "message": f"Cannot select '{skill}'. Supported skills: {', '.join(SKILLS_CATALOG.keys())}"
        }
    
    session = session_manager.get_or_create(session_id)
    session.selected_skill = matched
    return {
        "status": "success",
        "session_id": session_id,
        "selected_skill": matched,
        "message": f"Skill successfully set to {matched}."
    }

@mcp_server.tool()
def get_next_question(session_id: str, skill: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves a suitable primary technical question for the active session, avoiding duplicates.
    
    Args:
        session_id: Active session identifier.
        skill: Optional skill name. If omitted, uses the session's selected skill.
    """
    session = session_manager.get_or_create(session_id)
    target_skill = skill or session.selected_skill
    if not target_skill:
        return {
            "status": "error",
            "message": "No skill selected for this session. Please select a skill first."
        }
    
    # Enforce 3 primary questions limit deterministically
    if not session.can_ask_primary_question():
        return {
            "status": "limit_reached",
            "message": f"Primary question limit of {session.max_primary_questions} reached for this interview.",
            "primary_question_count": session.primary_question_count
        }
    
    # Filter questions for this skill that haven't been presented yet
    available = [
        q for q in QUESTIONS_CATALOG
        if q.skill.lower() == target_skill.lower() and q.id not in session.presented_questions
    ]
    
    if not available:
        # Fallback to any remaining question in the catalog for this skill
        available = [q for q in QUESTIONS_CATALOG if q.skill.lower() == target_skill.lower()]
    
    if not available:
        return {
            "status": "error",
            "message": f"No questions found for skill '{target_skill}'."
        }
    
    # Select question
    selected = available[0]
    return {
        "status": "success",
        "question": {
            "id": selected.id,
            "skill": selected.skill,
            "topic": selected.topic,
            "subtopic": selected.subtopic,
            "difficulty": selected.difficulty,
            "question_text": selected.question_text,
            "expected_concepts": selected.expected_concepts,
            "question_type": selected.question_type
        },
        "remaining_primary_allowance": session.max_primary_questions - session.primary_question_count
    }

@mcp_server.tool()
def save_interview_response(session_id: str, question_id: str, answer_text: str, concepts_identified: Optional[List[str]] = None, missing_concepts: Optional[List[str]] = None) -> Dict[str, Any]:
    """Saves candidate answer and identified concepts to in-memory session memory.
    
    Args:
        session_id: Active session identifier.
        question_id: The ID of the question being answered.
        answer_text: Spoken answer transcription.
        concepts_identified: List of key technical concepts candidate articulated.
        missing_concepts: List of concepts that candidate omitted or got unclear.
    """
    session = session_manager.get_or_create(session_id)
    concepts = concepts_identified or []
    missing = missing_concepts or []
    q_text = session.current_question_text or question_id
    
    session.record_answer(
        question_id=question_id,
        question_text=q_text,
        answer_text=answer_text,
        concepts_identified=concepts,
        missing_concepts=missing
    )
    
    return {
        "status": "success",
        "session_id": session_id,
        "recorded_concepts": concepts,
        "total_answers_in_session": len(session.candidate_answers)
    }
