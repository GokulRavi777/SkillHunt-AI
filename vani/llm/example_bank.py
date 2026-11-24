from typing import Dict, List
from pydantic import BaseModel

class PromptExample(BaseModel):
    category: str  # conceptual, implementation, scenario, elaboration, follow_up, cross_question, clarification
    skill: str
    context: str
    candidate_answer: str = ""
    example_question: str
    rationale: str

EXAMPLE_BANK: List[PromptExample] = [
    # 1. Primary Conceptual Questions
    PromptExample(
        category="conceptual",
        skill="Python",
        context="Candidate is starting a Python beginner interview on Lists and Tuples.",
        example_question="Could you explain the difference between a list and a tuple in Python, and give an example of when you would use each?",
        rationale="Clear, conversational, tests foundational mental model of mutability."
    ),
    PromptExample(
        category="conceptual",
        skill="Java",
        context="Candidate is interviewing on Java Memory Management & JVM internals.",
        example_question="How does the JVM differentiate between Heap and Stack memory during execution?",
        rationale="Direct conceptual question testing understanding of object allocation and call frames."
    ),
    PromptExample(
        category="conceptual",
        skill="JavaScript",
        context="Candidate is interviewing on JavaScript Async concurrency.",
        example_question="Can you explain how the JavaScript event loop coordinates the call stack and microtask queue?",
        rationale="Tests core concurrency mental model without confusing syntax."
    ),

    # 2. Practical Implementation Questions
    PromptExample(
        category="implementation",
        skill="Python",
        context="Candidate understands functions conceptually; testing function definition and return syntax.",
        candidate_answer="A function is a reusable block of code defined with def.",
        example_question="Could you explain how a function passes back a calculated result to the caller, and what it returns if you don't include a return statement?",
        rationale="Pushes from theoretical definition to understanding return values and None."
    ),
    PromptExample(
        category="implementation",
        skill="SQL",
        context="Candidate understands indexes; testing query optimization technique.",
        candidate_answer="Indexes make queries faster by building a B-tree.",
        example_question="If a query with multiple WHERE conditions is still doing a sequential scan, how would you create a composite index to optimize it?",
        rationale="Tests real-world column ordering in composite B-tree indexes."
    ),

    # 3. Scenario-based Questions
    PromptExample(
        category="scenario",
        skill="Docker",
        context="Candidate knows container basics; testing production incident scenario.",
        candidate_answer="Containers run isolated processes on top of the host kernel.",
        example_question="Suppose a containerized microservice crashes with an out-of-memory error under peak load. How would you diagnose and constrain its memory limits?",
        rationale="Simulates real-world production triage using cgroup memory parameters."
    ),
    PromptExample(
        category="scenario",
        skill="React",
        context="Candidate understands hooks; evaluating complex state re-render scenario.",
        candidate_answer="React re-renders components whenever state or props change.",
        example_question="If typing in a search input causes a noticeable lag across a long product list, how would you diagnose and eliminate unnecessary re-renders?",
        rationale="Tests practical performance profiling with useMemo, useCallback, or debounce."
    ),

    # 4. Short-Answer Elaboration
    PromptExample(
        category="elaboration",
        skill="Python",
        context="Candidate gave a very short, one-sentence answer on lists and tuples.",
        candidate_answer="Lists can change and tuples cannot.",
        example_question="That's right that lists are mutable while tuples are immutable. Could you share an example of a situation where you would prefer using a tuple over a list?",
        rationale="Acknowledges brevity gently and guides candidate to flesh out practical immutability."
    ),

    # 5. Contextual Follow-up (Adaptive to Answer Content)
    PromptExample(
        category="follow_up",
        skill="Python",
        context="Candidate explained dictionary key-value pairs and fast lookups.",
        candidate_answer="Dictionaries store key-value pairs and use hashing so looking up a key is O(1) time.",
        example_question="What kinds of data types are allowed to be used as keys in a Python dictionary, and why can't a list be a key?",
        rationale="Probes the connection between immutability, hashing, and dictionary keys."
    ),
    PromptExample(
        category="follow_up",
        skill="SQL",
        context="Candidate explained transactions and mentioned ACID properties.",
        candidate_answer="ACID stands for Atomicity, Consistency, Isolation, and Durability to prevent corrupted data.",
        example_question="Between Read Committed and Serializable isolation levels, what concurrency anomaly does Serializable prevent that Read Committed allows?",
        rationale="Contextual deep-dive targeting phantom reads and transaction isolation."
    ),

    # 6. Technical Cross-Questioning (Probing Edge Cases & Trade-offs)
    PromptExample(
        category="cross_question",
        skill="Java",
        context="Candidate claimed HashMap is completely thread-safe if keys are immutable.",
        candidate_answer="As long as the key is immutable like String, HashMap is safe to read across threads.",
        example_question="What happens when two threads concurrently put elements into a HashMap during an internal resize operation?",
        rationale="Respectfully challenges an unsafe assumption and probes race conditions/ConcurrentHashMap."
    ),
    PromptExample(
        category="cross_question",
        skill="JavaScript",
        context="Candidate stated that setTimeout with zero delay executes immediately.",
        candidate_answer="setTimeout with zero milliseconds runs immediately right after the current line.",
        example_question="If there are resolved Promises pending in the microtask queue, will the zero-delay setTimeout run before or after them?",
        rationale="Probes exact microtask vs macrotask execution order."
    ),

    # 7. Concept Clarification
    PromptExample(
        category="clarification",
        skill="React",
        context="Candidate confused useEffect with useLayoutEffect.",
        candidate_answer="useEffect runs synchronously right before the browser paints the screen.",
        example_question="Just to clarify, does useEffect run before or after the browser finishes the paint, and how does that compare to useLayoutEffect?",
        rationale="Gives the candidate an opportunity to correct a subtle timing misconception."
    ),
]

def get_examples_for_category(category: str, skill: str = "", limit: int = 2) -> List[PromptExample]:
    """Retrieves relevant examples matching the category and optionally the skill."""
    # First match category and skill
    matches = [e for e in EXAMPLE_BANK if e.category == category and (not skill or e.skill.lower() == skill.lower())]
    if len(matches) < limit:
        # Fill with any matches from the category
        fallback = [e for e in EXAMPLE_BANK if e.category == category and e not in matches]
        matches.extend(fallback)
    return matches[:limit]
