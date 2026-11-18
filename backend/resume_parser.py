"""Resume Parser & Technical Skills Identification Engine.

Section-Aware & Context-Intelligent:
- Detects and isolates the explicit 'SKILLS' section in the resume.
- Extracts technical skills strictly from the skills section to eliminate false positives
  (e.g., candidate initials like 'Gokul R' being misidentified as R language, or
  education grades like 'Grade: C' being misidentified as C language).
- Contextual boundary validation for short / ambiguous tokens (R, C, Go).
"""

from __future__ import annotations

import io
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

import pypdf

# Comprehensive Taxonomy of Technical Skills
TECHNICAL_SKILLS_TAXONOMY: dict[str, list[str]] = {
    "Programming Languages": [
        "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "C", "Go", "Golang",
        "Rust", "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "SQL", "Bash", "Shell"
    ],
    "Backend Frameworks & APIs": [
        "FastAPI", "Django", "Flask", "Express.js", "Express", "NestJS", "Node.js",
        "Spring Boot", "Spring", "ASP.NET", "Ruby on Rails", "FastMCP", "GraphQL",
        "REST API", "gRPC", "WebSockets", "Celery", "Kafka", "RabbitMQ"
    ],
    "Frontend Frameworks & UI": [
        "React", "React.js", "Next.js", "Vue", "Vue.js", "Angular", "Svelte",
        "Tailwind CSS", "Bootstrap", "HTML5", "CSS3", "Redux", "Zustand"
    ],
    "AI, ML & Voice": [
        "PyTorch", "TensorFlow", "Keras", "Scikit-Learn", "OpenCV", "LangChain",
        "LlamaIndex", "HuggingFace", "Transformers", "RAG", "Vector Databases",
        "Pinecone", "ChromaDB", "Milvus", "Qdrant", "Silero VAD", "ONNX", "ONNX Runtime",
        "Whisper", "ElevenLabs", "LiveKit", "WebRTC", "LLM Fine-tuning", "Prompt Engineering"
    ],
    "Databases & Caching": [
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "Cassandra",
        "Elasticsearch", "DynamoDB", "Oracle", "Firebase", "Supabase"
    ],
    "DevOps, Cloud & Infrastructure": [
        "Docker", "Kubernetes", "AWS", "Google Cloud", "GCP", "Microsoft Azure",
        "Terraform", "CI/CD", "GitHub Actions", "GitLab CI", "Linux", "Nginx",
        "Ansible", "Helm", "Prometheus", "Grafana", "OpenTelemetry"
    ],
    "System Design & Paradigms": [
        "AsyncIO", "Microservices", "Event-Driven Architecture", "Distributed Systems",
        "Caching Strategies", "Database Indexing", "Load Balancing", "Multithreading",
        "Object-Oriented Programming", "Design Patterns"
    ]
}

# Section Header Regex Patterns
SKILL_SECTION_HEADERS = [
    r"technical\s+skills",
    r"skills\s*(?:&|and)?\s*technologies",
    r"skills\s*(?:&|and)?\s*tools",
    r"technical\s+proficiencies",
    r"technical\s+expertise",
    r"core\s+competencies",
    r"tech\s+stack",
    r"programming\s+skills",
    r"key\s+skills",
    r"technical\s+strengths",
    r"skills",
    r"technologies",
]

NEXT_SECTION_HEADERS = [
    r"professional\s+experience",
    r"work\s+experience",
    r"employment\s+history",
    r"work\s+history",
    r"experience",
    r"academic\s+background",
    r"education",
    r"personal\s+projects",
    r"key\s+projects",
    r"projects",
    r"licenses\s*(?:&|and)?\s*certifications",
    r"certifications",
    r"publications",
    r"awards\s*(?:&|and)?\s*honors",
    r"achievements",
    r"volunteer\s+experience",
    r"languages\s+known",
    r"interests",
    r"references",
]

# Ambiguous single-letter/short token patterns that require strict context
STRICT_CONTEXT_SKILLS = {
    "R": re.compile(
        r"(?:\bR\s*(?:\(studio\)|studio|programming|language)(?!\w)|\b(?:programming|language)\s+in\s+R\b|(?<=[,\/\|\•\-\(\[])\s*R\s*(?=[,\/\|\•\-\(\)\],\n]))",
        re.IGNORECASE
    ),
    "C": re.compile(
        r"(?:\bC\s*[\/\+]\s*C\+\+|\bC\s+(?:programming|language)(?!\w)|(?<=[,\/\|\•\-\(\[])\s*C\s*(?=[,\/\|\•\-\(\)\],\n]))",
        re.IGNORECASE
    ),
    "Go": re.compile(
        r"(?:\b(?:Golang|Go\s+language|Go\s+programming)(?!\w)|(?<=[,\/\|\•\-\(\[])\s*Go\s*(?=[,\/\|\•\-\(\)\],\n]))",
        re.IGNORECASE
    ),
}

# Compile standard skill patterns
STANDARD_SKILL_PATTERNS: list[tuple[str, re.Pattern]] = []

for category, skills in TECHNICAL_SKILLS_TAXONOMY.items():
    for skill in skills:
        if skill in STRICT_CONTEXT_SKILLS:
            continue
        if skill.lower() in ["c++", "c#", ".net"]:
            pattern = re.compile(rf"(?<!\w){re.escape(skill)}(?!\w)", re.IGNORECASE)
        else:
            escaped = re.escape(skill).replace(r"\ ", r"\s+")
            pattern = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
        STANDARD_SKILL_PATTERNS.append((skill, pattern))


@dataclass
class ParsedResume:
    filename: str
    candidate_name: str
    target_role: str
    experience_years: int
    extracted_skills: list[str] = field(default_factory=list)
    skills_by_category: dict[str, list[str]] = field(default_factory=dict)
    skills_section_found: bool = False
    summary: str = ""
    raw_text_length: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "fileName": self.filename,
            "candidateName": self.candidate_name,
            "title": self.target_role,
            "experienceYears": self.experience_years,
            "extractedSkills": self.extracted_skills,
            "skillsByCategory": self.skills_by_category,
            "skillsSectionFound": self.skills_section_found,
            "summary": self.summary,
            "rawTextLength": self.raw_text_length,
        }


def extract_skills_section(text: str) -> tuple[str, bool]:
    """Isolate the explicit Skills section of the resume.

    Returns the isolated skills text block and a boolean indicating whether
    the section was explicitly detected.
    """
    header_pattern = r"(?:^|\n)\s*(?:[#\*\-_\s]*)(?P<header>" + "|".join(SKILL_SECTION_HEADERS) + r")(?:[#\*\-_\s]*)(?:[:\-]|\n)"
    match = re.search(header_pattern, text, re.IGNORECASE)

    if not match:
        return text, False

    start_pos = match.end()
    remaining_text = text[start_pos:]

    # Search for the next section header to bound the skills block
    next_pattern = r"(?:^|\n)\s*(?:[#\*\-_\s]*)(?:" + "|".join(NEXT_SECTION_HEADERS) + r")(?:[#\*\-_\s]*)(?:[:\-]|\n)"
    next_match = re.search(next_pattern, remaining_text, re.IGNORECASE)

    if next_match:
        skills_block = remaining_text[:next_match.start()].strip()
    else:
        # If no subsequent section is found, take up to the next 1500 characters
        skills_block = remaining_text[:1500].strip()

    return skills_block, True


def identify_technical_skills(
    text: str,
    candidate_name: str = ""
) -> tuple[list[str], dict[str, list[str]], bool]:
    """Identify technical skills strictly from the resume's skills section.

    Filters out candidate initials/name tokens and validates ambiguous tokens.
    """
    # 1. Isolate the skills section
    skills_text, section_found = extract_skills_section(text)

    # 2. Extract candidate name tokens to prevent initials from matching (e.g. 'R' in 'Gokul R')
    name_tokens = {token.strip().lower() for token in candidate_name.split() if token.strip()}

    extracted_set: set[str] = set()
    category_map: dict[str, list[str]] = {cat: [] for cat in TECHNICAL_SKILLS_TAXONOMY}

    # 3. Match standard unambiguous skills
    for skill, pattern in STANDARD_SKILL_PATTERNS:
        if pattern.search(skills_text):
            if skill not in extracted_set:
                extracted_set.add(skill)
                for cat, skill_list in TECHNICAL_SKILLS_TAXONOMY.items():
                    if skill in skill_list:
                        category_map[cat].append(skill)
                        break

    # 4. Strictly validate ambiguous short skills (R, C, Go)
    for skill, pattern in STRICT_CONTEXT_SKILLS.items():
        # Never match if skill token is identical to a candidate name token or initial
        if skill.lower() in name_tokens:
            continue

        # Look specifically in the skills section
        if pattern.search(skills_text):
            # Extra guard against false positives like "Grade C" or "Section C"
            if skill == "C":
                # Ensure it's not preceded by Grade / Section / Category
                if re.search(r"(?:grade|section|class|type|phase|vitamin)\s*[:\-]?\s*C\b", skills_text, re.IGNORECASE):
                    continue
            if skill not in extracted_set:
                extracted_set.add(skill)
                for cat, skill_list in TECHNICAL_SKILLS_TAXONOMY.items():
                    if skill in skill_list:
                        category_map[cat].append(skill)
                        break

    # 5. Consolidate aliases
    if "Golang" in extracted_set and "Go" in extracted_set:
        extracted_set.remove("Golang")
    if "React.js" in extracted_set and "React" in extracted_set:
        extracted_set.remove("React.js")
    if "Vue.js" in extracted_set and "Vue" in extracted_set:
        extracted_set.remove("Vue.js")

    cleaned_categories = {k: v for k, v in category_map.items() if v}
    sorted_skills = sorted(list(extracted_set), key=lambda s: s.lower())

    return sorted_skills, cleaned_categories, section_found


def extract_candidate_metadata(text: str, filename: str) -> tuple[str, str, int, str]:
    """Extract candidate name, target role, years of experience, and summary."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # Candidate Name extraction
    candidate_name = ""
    for line in lines[:6]:
        if re.search(r"resume|curriculum|vitae|email|phone|github|linkedin|page", line, re.IGNORECASE):
            continue
        words = line.split()
        if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w.isalpha()):
            candidate_name = " ".join(words)
            break

    if not candidate_name:
        base = os.path.splitext(filename)[0]
        cleaned_base = re.sub(r"[_\-\.]+", " ", base)
        cleaned_base = re.sub(r"resume|cv|profile", "", cleaned_base, flags=re.IGNORECASE).strip()
        candidate_name = cleaned_base.title() if cleaned_base else "Candidate"

    # Years of Experience
    exp_years = 3
    exp_matches = re.findall(r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)", text, re.IGNORECASE)
    if exp_matches:
        try:
            exp_years = min(30, max(1, int(exp_matches[0])))
        except ValueError:
            pass

    # Target Role
    role = "Software Engineer"
    role_patterns = [
        r"(Senior\s+(?:Backend|Frontend|Full\s*Stack|AI|ML|DevOps|Software)\s+Engineer)",
        r"((?:Backend|Frontend|Full\s*Stack|AI|ML|DevOps|Software|Systems)\s+Engineer)",
        r"((?:Machine\s+Learning|Data|Voice\s+AI|Cloud)\s+Engineer)",
        r"(Technical\s+Lead|Solutions\s+Architect|Engineering\s+Manager)"
    ]
    for pattern in role_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            role = match.group(1).title()
            break

    # Summary
    summary = ""
    summary_match = re.search(r"(?:Summary|Profile|About Me|Objective)[:\s]+(.*?)(?=\n\n|\n[A-Z\s]{4,}|\Z)", text, re.DOTALL | re.IGNORECASE)
    if summary_match:
        extracted_summary = summary_match.group(1).strip()
        summary = " ".join(extracted_summary.split())[:280] + ("..." if len(extracted_summary) > 280 else "")

    if not summary:
        summary = f"{role} with approximately {exp_years} years of demonstrated experience in building production software systems."

    return candidate_name, role, exp_years, summary


def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF byte content."""
    text_chunks: list[str] = []
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_chunks.append(page_text)
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {e}") from e
    return "\n".join(text_chunks).strip()


def extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX byte content using standard zipfile and xml parsing."""
    import zipfile
    text_chunks: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            xml_bytes = z.read("word/document.xml")
            tree = ET.fromstring(xml_bytes)
            for p in tree.iter():
                if p.tag.endswith("}p"):
                    para_text = "".join(node.text for node in p.iter() if node.text)
                    if para_text.strip():
                        text_chunks.append(para_text.strip())
    except Exception as e:
        raise ValueError(f"Failed to extract text from DOCX: {e}") from e
    return "\n".join(text_chunks).strip()


def extract_text_from_txt(content: bytes) -> str:
    """Extract text from plain text or markdown byte content."""
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1", errors="ignore")


def extract_raw_text(filename: str, content: bytes) -> str:
    """Detect file format from extension and extract raw string content."""
    ext = os.path.splitext(filename.lower())[1]
    if ext == ".pdf":
        return extract_text_from_pdf(content)
    elif ext in [".docx", ".doc"]:
        return extract_text_from_docx(content)
    elif ext in [".txt", ".md", ".rtf"]:
        return extract_text_from_txt(content)
    else:
        try:
            return extract_text_from_txt(content)
        except Exception:
            return extract_text_from_pdf(content)


def parse_resume(filename: str, content: bytes) -> ParsedResume:
    """Parse resume content using section-aware skill extraction."""
    raw_text = extract_raw_text(filename, content)
    if not raw_text or len(raw_text.strip()) < 10:
        raise ValueError("Resume file appears empty or text could not be extracted.")

    # 1. Candidate metadata first (to isolate name tokens)
    candidate_name, role, exp_years, summary = extract_candidate_metadata(raw_text, filename)

    # 2. Extract technical skills strictly from the skills section
    skills, skills_by_cat, section_found = identify_technical_skills(raw_text, candidate_name=candidate_name)

    return ParsedResume(
        filename=filename,
        candidate_name=candidate_name,
        target_role=role,
        experience_years=exp_years,
        extracted_skills=skills,
        skills_by_category=skills_by_cat,
        skills_section_found=section_found,
        summary=summary,
        raw_text_length=len(raw_text)
    )
