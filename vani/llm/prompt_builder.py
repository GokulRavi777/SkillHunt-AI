from typing import List, Dict, Any, Optional
from vani.llm.example_bank import get_examples_for_category, PromptExample
from vani.llm.prompts import UNIFIED_EVALUATION_AND_QUESTION_PROMPT

class PromptBuilder:
    """Dynamically constructs context-rich one-shot/few-shot prompts for question generation."""

    @staticmethod
    def build_primary_question_prompt(
        skill: str,
        topic: str,
        subtopic: str,
        difficulty: str,
        question_type: str,
        previously_asked_questions: List[str],
        concepts_explored: List[str],
        remaining_primary_allowance: int,
    ) -> str:
        # Select 1 or 2 relevant examples from example bank
        examples: List[PromptExample] = get_examples_for_category(question_type, skill=skill, limit=2)
        
        example_text = ""
        for i, ex in enumerate(examples, 1):
            example_text += f"\n[Example {i} - {ex.category.capitalize()}]\n"
            example_text += f"Context: {ex.context}\n"
            example_text += f"Question: \"{ex.example_question}\"\n"
            example_text += f"Rationale: {ex.rationale}\n"

        prompt = f"""You are generating a primary technical interview question for a candidate.

INTERVIEW CONTEXT:
- Skill: {skill}
- Topic: {topic}
- Subtopic: {subtopic}
- Intended Difficulty: {difficulty}
- Question Type: {question_type}
- Previously Asked Questions in this Session: {previously_asked_questions or 'None'}
- Concepts Already Explored: {concepts_explored or 'None'}
- Remaining Primary Questions Allowed: {remaining_primary_allowance}

REFERENCE EXAMPLES (Few-shot guidance):
{example_text}

REQUIREMENTS:
1. Generate exactly ONE spoken technical question tailored to {skill} and topic '{topic}'.
2. The question must NOT duplicate any previously asked question.
3. Keep it conversational, clear, and direct (under 35 words).
4. Do NOT use markdown, bullet points, asterisks, or code snippets.
5. Provide your output strictly in JSON:
{{
  "question_text": "The exact spoken question to ask the candidate",
  "topic": "{topic}",
  "subtopic": "{subtopic}",
  "difficulty": "{difficulty}",
  "expected_concepts": ["concept1", "concept2", "concept3"]
}}
"""
        return prompt

    @staticmethod
    def build_follow_up_prompt(
        skill: str,
        primary_question: str,
        candidate_answer: str,
        concepts_identified: List[str],
        missing_concepts: List[str],
        concepts_already_explored: List[str],
        follow_up_history: List[Dict[str, Any]],
        remaining_follow_up_allowance: int,
        follow_up_type: str = "follow_up", # "follow_up", "cross_question", "elaboration", "clarification"
    ) -> str:
        # Select 1-2 examples matching follow_up_type
        examples = get_examples_for_category(follow_up_type, skill=skill, limit=2)
        
        example_text = ""
        for i, ex in enumerate(examples, 1):
            example_text += f"\n[Example {i} - {ex.category.capitalize()}]\n"
            example_text += f"Context: {ex.context}\n"
            if ex.candidate_answer:
                example_text += f"Candidate Answer: \"{ex.candidate_answer}\"\n"
            example_text += f"Follow-up: \"{ex.example_question}\"\n"
            example_text += f"Rationale: {ex.rationale}\n"

        prompt = f"""You are generating an adaptive follow-up or cross-question based directly on the candidate's actual answer.

SESSION STATE:
- Skill: {skill}
- Original Primary Question: "{primary_question}"
- Candidate's Actual Spoken Answer: "{candidate_answer}"
- Technical Concepts Identified in Answer: {concepts_identified or 'None'}
- Missing or Unclear Concepts: {missing_concepts or 'None'}
- Concepts Already Explored in Session: {concepts_already_explored or 'None'}
- Previous Follow-ups for this Question: {len(follow_up_history)}
- Remaining Follow-up Allowance for this Question: {remaining_follow_up_allowance}
- Follow-up Strategy: {follow_up_type}

REFERENCE EXAMPLES:
{example_text}

TASK:
1. Analyze the candidate's specific claims and vocabulary.
2. Formulate exactly ONE relevant follow-up or cross-question directly connected to what they just said.
   - If they gave an incomplete definition, probe the missing mechanism or trade-off.
   - If they gave a strong answer, probe an edge case, failure scenario, or deeper implementation detail.
   - If they gave a very brief answer, ask them to elaborate on how the mechanism functions.
3. Keep the spoken question natural, respectful, and under 35 words.
4. Do NOT use markdown, asterisks, bullet points, or code formatting.

Output strictly valid JSON:
{{
  "acknowledgment": "A brief 5-10 word spoken acknowledgment of their answer (e.g. 'That makes sense regarding the wrapper.')",
  "question_text": "The spoken follow-up question directly probing their answer",
  "target_concept": "The specific technical concept being probed",
  "question_type": "{follow_up_type}"
}}
"""
        return prompt

    @staticmethod
    def build_unified_turn_prompt(
        skill: str,
        topic: str,
        subtopic: str,
        current_question: str,
        expected_concepts: List[str],
        candidate_utterance: str,
        primary_question_count: int,
        max_primary_questions: int,
        follow_up_count: int,
        max_follow_ups: int,
        concepts_explored: List[str],
    ) -> str:
        # Retrieve curated representative few-shot examples
        fu_examples = get_examples_for_category("follow_up", skill=skill, limit=1)
        cross_examples = get_examples_for_category("cross_question", skill=skill, limit=1)
        elab_examples = get_examples_for_category("elaboration", skill=skill, limit=1)

        examples = fu_examples + cross_examples + elab_examples
        example_text = ""
        for i, ex in enumerate(examples, 1):
            example_text += f"\n[Example {i} - {ex.category.capitalize()}]\n"
            if ex.candidate_answer:
                example_text += f"Candidate Answer: \"{ex.candidate_answer}\"\n"
            example_text += f"Follow-up: \"{ex.example_question}\"\n"
            example_text += f"Rationale: {ex.rationale}\n"

        remaining_fu = max_follow_ups - follow_up_count

        return UNIFIED_EVALUATION_AND_QUESTION_PROMPT.format(
            selected_skill=skill,
            topic=topic,
            subtopic=subtopic,
            current_question=current_question,
            expected_concepts=", ".join(expected_concepts) if expected_concepts else "Core concepts",
            primary_question_count=primary_question_count,
            max_primary_questions=max_primary_questions,
            follow_up_count=follow_up_count,
            max_follow_ups=max_follow_ups,
            concepts_explored=", ".join(concepts_explored) if concepts_explored else "None",
            remaining_follow_ups=remaining_fu,
            candidate_utterance=candidate_utterance,
            few_shot_examples=example_text,
        )

prompt_builder = PromptBuilder()
