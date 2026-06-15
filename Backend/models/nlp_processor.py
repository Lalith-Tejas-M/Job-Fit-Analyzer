import re
import json
import spacy
import numpy as np
from transformers import pipeline
import dateparser
from dateutil.relativedelta import relativedelta
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity

# =============================================================================
# Global Singletons (Lazy Loaded)
# =============================================================================
nlp = None
skill_ner = None
sbert_model = None
canonical_embeddings = None

# Pre-cached SBERT anchor embeddings (computed once, reused on every API call)
_skill_anchor_embs = None   # For skill extraction
_role_anchor_embs  = None   # For experience role detection
_cert_anchor_embs  = None   # For certification detection
_proj_skill_anchor_embs = None  # For project tech stack extraction
_domain_embs = None          # FIX 4: cached domain embeddings for project classification

# =============================================================================
# LLM Extraction Cache (Ensures ONE call per resume)
# =============================================================================
_llm_cache = {}

def _get_llm_data(text: str) -> dict | None:
    """
    Fetches LLM extraction, caching ONLY successful results by text hash.
    Failures (None) are NEVER cached — so re-uploading the same resume will
    retry the LLM instead of immediately going to fallback.
    """
    import hashlib
    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
    if text_hash in _llm_cache:
        return _llm_cache[text_hash]

    # Clear old cache entries to avoid memory leaks
    _llm_cache.clear()

    from models.llm_resume_parser import parse_resume_with_llm
    data = parse_resume_with_llm(text)

    # Only cache successful extractions
    if data is not None:
        _llm_cache[text_hash] = data

        # Log Extraction Metadata
        if "metadata" in data:
            print("\n" + "=" * 40)
            print("  LLM EXTRACTION METADATA")
            print("=" * 40)
            import json
            print(json.dumps(data["metadata"], indent=2))
            print("=" * 40 + "\n")

    return data

# =============================================================================
# Skill Blacklist — generic English words + project/action words NEVER skills
# FIX 1: expanded to prevent project names / sentences from leaking in
# =============================================================================
SKILL_BLACKLIST = {
    # Generic English words
    "learn", "learning", "agent", "project", "projects", "application", "applications",
    "technology", "framework", "system", "tool", "skills", "skill",
    "work", "working", "experience", "knowledge", "use", "using",
    "develop", "development", "build", "building", "management",
    "data", "model", "models", "service", "services", "team",
    "approach", "solution", "solutions", "concept", "concepts",
    "ability", "methods", "technique", "techniques", "various",
    "include", "including", "following", "exposure", "understanding",
    "strong", "good", "basic", "advanced", "intermediate", "level",
    "year", "years", "month", "months", "intern", "internship",
    "training", "trainee", "assistant", "researcher",
    "cgpa", "gpa", "percentage",  # academic metrics
    "tech",                        # too generic alone
    # Project/action words (FIX 1: new additions)
    "powered", "based", "driven", "enabled", "oriented",
    "analyzer", "analyser", "planner", "generator", "detector",
    "recommendation", "recommendations", "intelligent", "personalized",
    "itinerary", "trip", "tourism", "interface", "platform",
    "real", "world", "problems", "practical", "motivated", "detail",
    "routes", "mapping", "optimized", "interactive", "multi", "key",
    "major", "mini", "capstone", "academic", "personal",
    "overview", "summary", "profile", "objective", "contact",
    "linkedin", "github", "email", "phone", "address",
    "university", "college", "institute", "school", "education",
    "bachelor", "master", "degree", "engineering", "science",
    "built", "created", "developed", "implemented", "designed",
    "an", "a", "the", "is", "are", "was", "were", "for", "of",
    "and", "or", "in", "on", "with", "using", "via",
    "unknown", "unspecified", "none", "null", "nil", "undefined",
}

# FIX 1: Words that indicate a chunk is a sentence/project title, not a skill
_SENTENCE_STARTER_WORDS = {
    "an", "a", "the", "build", "built", "develop", "developed", "design",
    "designed", "create", "created", "implement", "implemented",
    "i", "we", "this", "our", "my",
}

# =============================================================================
# Section header patterns — permissive: allow trailing colon/dash, mixed case,
# varying whitespace, and single-line or end-of-line occurrence.
# =============================================================================

# All known section keywords in one master list (used to detect section boundaries)
_ALL_SECTION_KEYWORDS = (
    r'PROJECTS?|ACADEMIC\s+PROJECTS?|PERSONAL\s+PROJECTS?|KEY\s+PROJECTS?|'
    r'RELEVANT\s+PROJECTS?|PROJECT\s+WORK|MAJOR\s+PROJECTS?|MINI\s+PROJECTS?|'
    r'CAPSTONE\s+PROJECT|'
    r'EXPERIENCE|WORK\s+EXPERIENCE|PROFESSIONAL\s+EXPERIENCE|'
    r'INTERNSHIP|INTERNSHIPS?|TRAINING|TRAININGS?|EMPLOYMENT|WORK\s+HISTORY|'
    r'CAREER\s+SUMMARY|INDUSTRY\s+EXPERIENCE|RESEARCH\s+EXPERIENCE|'
    r'VOLUNTEER\s+EXPERIENCE|'
    r'EDUCATION|EDUCATIONAL\s+BACKGROUND|ACADEMIC\s+BACKGROUND|'
    r'QUALIFICATIONS?|ACADEMIC\s+QUALIFICATIONS?|'
    r'SKILLS?|TECHNICAL\s+SKILLS?|CORE\s+COMPETENCIES|KEY\s+SKILLS?|'
    r'AREAS\s+OF\s+EXPERTISE|TECHNOLOGIES|TOOLS?\s+AND\s+TECHNOLOGIES?|'
    r'PROGRAMMING\s+SKILLS?|'
    r'CERTIFICATIONS?|CERTIFICATES?|LICENSES?|PROFESSIONAL\s+CERTIFICATIONS?|'
    r'COURSES?|ONLINE\s+COURSES?|ACHIEVEMENTS?|AWARDS?|'
    r'OBJECTIVE|SUMMARY|PROFILE|CONTACT|PUBLICATIONS?|REFERENCES?|'
    r'LANGUAGES?|HOBBIES|INTERESTS'
)

# A header line is: optional whitespace, keyword, optional trailing [:–-]?,
# optional trailing whitespace — at start of line.
_HEADER_LINE_RE = re.compile(
    r'^\s*(' + _ALL_SECTION_KEYWORDS + r')\s*[:\-–]?\s*$',
    re.IGNORECASE | re.MULTILINE
)

SECTION_HEADER_PATTERNS = {
    "projects": re.compile(
        r'^\s*(PROJECTS?|ACADEMIC\s+PROJECTS?|PERSONAL\s+PROJECTS?|'
        r'KEY\s+PROJECTS?|RELEVANT\s+PROJECTS?|PROJECT\s+WORK|'
        r'MAJOR\s+PROJECTS?|MINI\s+PROJECTS?|CAPSTONE\s+PROJECT)\s*[:\-–]?\s*$',
        re.IGNORECASE | re.MULTILINE
    ),
    "experience": re.compile(
        r'^\s*(EXPERIENCE|WORK\s+EXPERIENCE|PROFESSIONAL\s+EXPERIENCE|'
        r'INTERNSHIP|INTERNSHIPS?|TRAINING|TRAININGS?|EMPLOYMENT|'
        r'WORK\s+HISTORY|CAREER\s+SUMMARY|INDUSTRY\s+EXPERIENCE|'
        r'RESEARCH\s+EXPERIENCE|VOLUNTEER\s+EXPERIENCE)\s*[:\-–]?\s*$',
        re.IGNORECASE | re.MULTILINE
    ),
    "education": re.compile(
        r'^\s*(EDUCATION|EDUCATIONAL\s+BACKGROUND|ACADEMIC\s+BACKGROUND|'
        r'QUALIFICATIONS?|ACADEMIC\s+QUALIFICATIONS?)\s*[:\-–]?\s*$',
        re.IGNORECASE | re.MULTILINE
    ),
    "skills": re.compile(
        r'^\s*(SKILLS?|TECHNICAL\s+SKILLS?|CORE\s+COMPETENCIES|'
        r'KEY\s+SKILLS?|AREAS\s+OF\s+EXPERTISE|TECHNOLOGIES|'
        r'TOOLS?\s+AND\s+TECHNOLOGIES?|PROGRAMMING\s+SKILLS?)\s*[:\-–]?\s*$',
        re.IGNORECASE | re.MULTILINE
    ),
    "certifications": re.compile(
        r'^\s*(CERTIFICATIONS?|CERTIFICATES?|LICENSES?|'
        r'PROFESSIONAL\s+CERTIFICATIONS?|COURSES?|ONLINE\s+COURSES?|'
        r'ACHIEVEMENTS?|AWARDS?)\s*[:\-–]?\s*$',
        re.IGNORECASE | re.MULTILINE
    ),
}

# =============================================================================
# MASTER SKILLS list — curated tech terms only
# =============================================================================
MASTER_SKILLS = [
    "AWS", "Google Cloud", "Azure", "Machine Learning", "Deep Learning", "AI", "NLP",
    "Computer Vision", "Python", "Java", "JavaScript", "TypeScript", "C++",
    "C#", "Go", "Rust", "PHP", "Ruby", "Swift", "Kotlin", "R", "Scala",
    "Bash", "NumPy", "Pandas", "Scikit-learn", "TensorFlow", "PyTorch",
    "Keras", "OpenCV", "HuggingFace", "LangChain", "CrewAI", "LlamaIndex",
    "NLTK", "spaCy", "Matplotlib", "Seaborn", "XGBoost", "LightGBM",
    "Flask", "Django", "FastAPI", "Spring Boot", "Express.js", "Node.js",
    "React", "Angular", "Vue.js", "SQL", "MySQL", "PostgreSQL", "MongoDB",
    "Redis", "Elasticsearch", "Cassandra", "SQLite", "Docker", "Kubernetes",
    "Git", "GitHub", "GitLab", "Jenkins", "Ansible", "Terraform",
    "Linux", "Airflow", "Kafka", "Apache Spark", "Hadoop", "Tableau",
    "Power BI", "REST API", "GraphQL", "Agile", "Scrum", "MLOps", "LLM", "RAG",
    "HTML", "CSS", "Bootstrap", "Tailwind", "jQuery", "Next.js", "Vite",
    "Android", "iOS", "Flutter", "React Native", "Firebase",
    "Selenium", "Playwright", "Pytest", "JUnit", "CI/CD", "DevOps",
    "BERT", "GPT", "Transformer", "Langchain", "Ollama",
]

# =============================================================================
# Helpers
# =============================================================================
def _get_sbert():
    global sbert_model
    if sbert_model is None:
        from models.embeddings import model as _m
        sbert_model = _m
    return sbert_model


def _get_skill_anchors():
    """Return (and cache) SBERT embeddings for skill anchor phrases."""
    global _skill_anchor_embs
    if _skill_anchor_embs is None:
        sbert = _get_sbert()
        _skill_anchor_embs = sbert.encode(
            ["Programming Language", "Software Framework", "Technical Skill", "Library Tool"],
            convert_to_tensor=True
        ).cpu().numpy()
    return _skill_anchor_embs


def _get_role_anchors():
    """Return (and cache) SBERT embeddings for job-role anchor phrases."""
    global _role_anchor_embs
    if _role_anchor_embs is None:
        sbert = _get_sbert()
        _role_anchor_embs = sbert.encode(
            ['Software Engineer', 'Data Scientist', 'Manager', 'Developer', 'Analyst',
             'Consultant', 'Intern', 'Trainee', 'Research Assistant', 'Designer',
             'Architect', 'Lead', 'Associate', 'Specialist'],
            convert_to_tensor=True
        ).cpu().numpy()
    return _role_anchor_embs


def _get_cert_anchors():
    """Return (and cache) SBERT embeddings for certification detection."""
    global _cert_anchor_embs
    if _cert_anchor_embs is None:
        sbert = _get_sbert()
        _cert_anchor_embs = sbert.encode(
            ["Professional Certification Certificate Credential Course Award"],
            convert_to_tensor=True
        ).cpu().numpy()
    return _cert_anchor_embs


def _get_proj_skill_anchors():
    """Return (and cache) SBERT embeddings for project tech-stack extraction."""
    global _proj_skill_anchor_embs
    if _proj_skill_anchor_embs is None:
        sbert = _get_sbert()
        _proj_skill_anchor_embs = sbert.encode(
            ["Programming Language", "Software Framework", "Technical Library Tool"],
            convert_to_tensor=True
        ).cpu().numpy()
    return _proj_skill_anchor_embs


def _get_domain_embeddings():
    """FIX 4: Cache domain label embeddings once — not re-encoded per request."""
    global _domain_embs
    if _domain_embs is None:
        sbert = _get_sbert()
        _domain_labels = [
            "Web Development",
            "AI and Machine Learning",
            "Data Science and Analytics",
            "DevOps and Cloud",
            "Mobile App Development",
            "Cybersecurity",
            "General Software"
        ]
        _domain_embs = (
            _domain_labels,
            sbert.encode(_domain_labels, convert_to_tensor=True).cpu().numpy()
        )
    return _domain_embs


def get_nlp_model():
    """
    Lazy-load spaCy + JobBERT skill NER once and return spaCy model.
    """
    global nlp, skill_ner
    if nlp is None:
        try:
            nlp = spacy.load('en_core_web_sm')
        except OSError:
            print("Downloading spaCy model (en_core_web_sm)...")
            spacy.cli.download('en_core_web_sm')
            nlp = spacy.load('en_core_web_sm')
    if skill_ner is None:
        print("Loading JobBERT skill NER (jjzha/jobbert_skill_extraction)...")
        print("  [First run: downloading ~440MB model from HuggingFace, please wait]")
        skill_ner = pipeline(
            "token-classification",
            model="jjzha/jobbert_skill_extraction",
            aggregation_strategy="first",
            device=-1,
        )
        print("  JobBERT skill NER loaded.")
    return nlp


def _is_sentence_fragment(text: str) -> bool:
    """
    FIX 1: Detect if a candidate skill is actually a sentence/project-name fragment.
    Returns True if it should be REJECTED.
    """
    words = text.strip().split()
    if not words:
        return True
    # More than 4 words → likely a phrase/title, not a skill
    if len(words) > 4:
        return True
    # Starts with a sentence-starting word (determiner, verb, pronoun)
    if words[0].lower() in _SENTENCE_STARTER_WORDS:
        return True
    # Contains a bullet separator like "•" or "–"
    if any(c in text for c in "•–—"):
        return True
    return False


def _normalize_skill_batch(raw_skills: list) -> list:
    """
    FIX 4: Batch-encode ALL raw skills at once instead of one-at-a-time.
    Returns list of (raw, normalized) tuples. Much faster than calling
    _normalize_skill() in a loop.
    """
    if not raw_skills:
        return []

    sbert = _get_sbert()

    # Blacklist + sentence filter first (cheap)
    candidates = []
    for s in raw_skills:
        stripped = s.strip()
        if not stripped or len(stripped) < 2:
            continue
        if stripped.lower() in SKILL_BLACKLIST:
            continue
        if _is_sentence_fragment(stripped):
            continue
        candidates.append(stripped)

    if not candidates:
        return []

    # Exact match fast-path
    global canonical_embeddings
    results = []
    needs_sbert = []

    for c in candidates:
        c_title = c.title()
        if c_title in MASTER_SKILLS:
            results.append(c_title)
        elif c in MASTER_SKILLS:
            results.append(c)
        else:
            needs_sbert.append(c)

    if needs_sbert:
        # Lazy-compute MASTER_SKILLS embeddings once
        if canonical_embeddings is None:
            canonical_embeddings = sbert.encode(
                MASTER_SKILLS, convert_to_tensor=True
            ).cpu().numpy()

        # Batch encode all remaining candidates in ONE forward pass
        cand_embs = sbert.encode(needs_sbert, convert_to_tensor=True).cpu().numpy()
        # cosine_similarity: (N_candidates, N_master)
        sim_matrix = cosine_similarity(cand_embs, canonical_embeddings)

        for i, cand in enumerate(needs_sbert):
            best_idx = int(np.argmax(sim_matrix[i]))
            best_score = float(sim_matrix[i][best_idx])
            if best_score > 0.85:
                results.append(MASTER_SKILLS[best_idx])
            else:
                # Keep the original if it looks like a real tech word (CamelCase or acronym)
                if len(cand) >= 2 and (cand[0].isupper() or cand.isupper()):
                    results.append(cand.title())
                # else drop it — too vague

    return list(set(results))


_resume_sentences_cache = {}

def _verify_entity(entity: str, text: str, sbert, threshold: float = 0.5) -> bool:
    """
    Verification Layer: Prevents LLM hallucinations by checking the extracted
    entity actually appears in resume text (exact or semantic match).
    """
    if not entity or not text:
        return False

    entity_lower = entity.lower()
    text_lower = text.lower()

    # 1. Exact Substring Match (Fast Path)
    clean_entity = re.sub(r'[^\w\s]', '', entity_lower)
    clean_text = re.sub(r'[^\w\s]', '', text_lower)
    if clean_entity in clean_text:
        return True

    # 2. Semantic Match against lines
    import hashlib
    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()

    global _resume_sentences_cache
    if text_hash not in _resume_sentences_cache:
        _resume_sentences_cache.clear()
        lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 5]
        if not lines:
            return False
        line_embs = sbert.encode(lines, convert_to_tensor=True).cpu().numpy()
        _resume_sentences_cache[text_hash] = line_embs

    line_embs = _resume_sentences_cache[text_hash]
    entity_emb = sbert.encode([entity], convert_to_tensor=True).cpu().numpy()
    scores = cosine_similarity(entity_emb, line_embs)[0]
    return float(np.max(scores)) >= threshold


def _extract_section_text(text: str, section_key: str) -> str:
    """
    Locate a named section in raw resume text using header regex patterns.
    Returns the text block from the section header until the next section header.
    """
    target_pattern = SECTION_HEADER_PATTERNS.get(section_key)
    if not target_pattern:
        return ""

    target_match = target_pattern.search(text)
    if not target_match:
        print(f"  [SECTION] '{section_key}' header NOT FOUND in text.")
        return ""

    print(f"  [SECTION] '{section_key}' found at char {target_match.start()}: repr={repr(target_match.group(0)[:40])}")
    section_start = target_match.end()

    next_section_match = None
    for m in _HEADER_LINE_RE.finditer(text, section_start):
        if m.start() > section_start:
            next_section_match = m
            break

    if next_section_match:
        block = text[section_start:next_section_match.start()].strip()
    else:
        block = text[section_start:].strip()

    print(f"  [SECTION] '{section_key}' block length={len(block)} chars")
    return block


# =============================================================================
# Extraction Pipelines
# =============================================================================

def extract_skills(text: str, nlp_model) -> list:
    """
    Skill Fusion Layer with FIX 1 (better filtering) + FIX 4 (batch SBERT):
    1. Extract from Skills section + summary using JobBERT (FIX 4: targeted scan)
    2. Supplement with SBERT noun-chunk scoring (sentence-filtered)
    3. Merge LLM skills (confidence >= 0.60)
    4. Harvest tech_stack from LLM projects section (FIX 1: correct source)
    5. Batch normalize via SBERT (FIX 4: one forward pass for all candidates)
    """
    global skill_ner
    raw_candidates = set()

    # FIX 4: Target only the skills section + resume summary (~2000 chars max)
    # instead of chunking the full resume through JobBERT multiple times
    skills_section = _extract_section_text(text, "skills")
    summary_text = text[:800]  # first 800 chars typically = name + summary/objective

    if skills_section:
        jobbert_target = (summary_text + "\n" + skills_section)[:2500]
    else:
        # If no skills section found, scan full resume in ONE chunk only
        jobbert_target = text[:2500]

    # ── Step 1: JobBERT Extraction (targeted scope) ───────────────────────────
    if skill_ner:
        try:
            ner_results = skill_ner(jobbert_target)
            for ent in ner_results:
                if ent.get("score", 0) >= 0.50:
                    word = ent["word"].replace("##", "").strip()
                    if len(word) >= 2 and not word.isnumeric() and len(word.split()) <= 4:
                        raw_candidates.add(word)
        except Exception as e:
            print(f"[JobBERT NER] Error: {e}")

    # ── Step 2: SBERT Noun-Chunk Scoring (FIX 1: filter sentence starters) ───
    if nlp_model:
        sbert = _get_sbert()
        # Run spaCy on skills section or top 2000 chars
        parse_target = (skills_section + "\n" + summary_text)[:2000] if skills_section else text[:2000]
        doc = nlp_model(parse_target)
        skill_anchors = _get_skill_anchors()
        chunk_texts = []
        chunk_valids = []
        for chunk in doc.noun_chunks:
            candidate = chunk.text.replace('\n', ' ').strip()
            words = candidate.split()
            # FIX 1: reject if first word is a sentence starter / determiner
            if not words or words[0].lower() in _SENTENCE_STARTER_WORDS:
                continue
            if not (1 <= len(words) <= 3):
                continue
            if candidate.lower() in SKILL_BLACKLIST:
                continue
            chunk_texts.append(candidate)
            chunk_valids.append(True)

        if chunk_texts:
            # FIX 4: batch encode all noun chunks at once
            chunk_embs = sbert.encode(chunk_texts, convert_to_tensor=True).cpu().numpy()
            scores = cosine_similarity(chunk_embs, skill_anchors).max(axis=1)
            for text_chunk, score in zip(chunk_texts, scores):
                if score > 0.60:
                    raw_candidates.add(text_chunk)

    # ── Step 3: LLM Skills (confidence >= 0.60) ──────────────────────────────
    llm_data = _get_llm_data(text)
    if llm_data and "skills" in llm_data:
        for sk_obj in llm_data.get("skills", []):
            if isinstance(sk_obj, dict):
                skill_name = sk_obj.get("skill", "")
                conf = float(sk_obj.get("confidence", 1.0))
                # FIX 1: reject if confidence low OR looks like a sentence
                if conf >= 0.60 and skill_name and not _is_sentence_fragment(skill_name):
                    raw_candidates.add(skill_name)
            elif isinstance(sk_obj, str) and not _is_sentence_fragment(sk_obj):
                raw_candidates.add(sk_obj)

    # ── Step 4: Harvest tech_stack from LLM projects (FIX 1: correct source) ─
    # This ensures tools mentioned IN projects are captured as skills,
    # but only the tech_stack field — not the project title/summary.
    if llm_data and "projects" in llm_data:
        for proj in llm_data.get("projects", []):
            if isinstance(proj, dict):
                for tech in proj.get("tech_stack", []):
                    if tech and isinstance(tech, str) and not _is_sentence_fragment(tech):
                        raw_candidates.add(tech.strip())

    # Fallback if ALL methods fail
    if not raw_candidates and not llm_data:
        return _extract_skills_fallback(text, nlp_model)

    # ── Step 5: Batch SBERT Normalization (FIX 4) ────────────────────────────
    normalized = _normalize_skill_batch(list(raw_candidates))

    print(f"  [Skills] Raw candidates: {len(raw_candidates)}, Normalized: {len(normalized)}")
    return normalized


def _extract_skills_fallback(text: str, nlp_model) -> list:
    """Fallback: JobBERT + SBERT noun-chunk on skills section only."""
    global skill_ner
    raw_candidates = set()
    sbert = _get_sbert()

    skills_section = _extract_section_text(text, "skills")
    target_text = (text[:800] + " " + skills_section)[:2500] if skills_section else text[:2500]

    if skill_ner:
        try:
            ner_results = skill_ner(target_text)
            for ent in ner_results:
                if ent.get("score", 0) >= 0.50:
                    word = ent["word"].replace("##", "").strip()
                    if len(word) >= 2 and not word.isnumeric() and len(word.split()) <= 4:
                        raw_candidates.add(word)
        except Exception as e:
            print(f"[Fallback JobBERT NER] Error: {e}")

    if nlp_model:
        doc = nlp_model(target_text[:2000])
        skill_anchors = _get_skill_anchors()
        chunk_texts = []
        for chunk in doc.noun_chunks:
            candidate = chunk.text.replace('\n', ' ').strip()
            words = candidate.split()
            if not words or words[0].lower() in _SENTENCE_STARTER_WORDS:
                continue
            if not (1 <= len(words) <= 3):
                continue
            if candidate.lower() in SKILL_BLACKLIST:
                continue
            chunk_texts.append(candidate)

        if chunk_texts:
            chunk_embs = sbert.encode(chunk_texts, convert_to_tensor=True).cpu().numpy()
            scores = cosine_similarity(chunk_embs, skill_anchors).max(axis=1)
            for text_chunk, score in zip(chunk_texts, scores):
                if score > 0.60:
                    raw_candidates.add(text_chunk)

    return _normalize_skill_batch(list(raw_candidates))


def extract_education(text: str, nlp_model) -> list:
    """
    Primary extractor: Uses LLM.
    Verifies extracted entities via text matching / SBERT.
    Falls back to legacy spaCy extraction if LLM fails.
    """
    llm_data = _get_llm_data(text)
    if not llm_data:
        return _extract_education_fallback(text, nlp_model)

    llm_edu = llm_data.get("education", [])
    if not llm_edu:
        return []

    sbert = _get_sbert()
    education_results = []

    for ed in llm_edu:
        if not isinstance(ed, dict): continue
        conf = float(ed.get("confidence", 1.0))
        if conf < 0.60: continue

        uni = ed.get("university", "")
        deg = ed.get("degree", "")

        verify_str = f"{deg} {uni}".strip()
        if verify_str and _verify_entity(verify_str, text, sbert, threshold=0.45):
            education_results.append({
                "degree": deg[:50] if deg else "Unknown Degree",
                "branch": ed.get("branch", "Unknown Branch")[:50],
                "university": uni[:100] if uni else "Unknown University",
                "year": str(ed.get("year", "Unknown"))[:10]
            })
        else:
            print(f"[Verification] Dropped hallucinated Education: {verify_str}")

    return education_results


def _extract_education_fallback(text: str, nlp_model) -> list:
    """Minimal spaCy NER fallback for Education."""
    if not nlp_model: return []
    doc = nlp_model(text[:3000])
    orgs = [ent.text.strip() for ent in doc.ents if ent.label_ == "ORG" and len(ent.text) > 3]
    return [{"degree": "Unknown", "branch": "Unknown", "university": org, "year": "Unknown"} for org in orgs[:2]]


def extract_experience(text: str, nlp_model) -> list:
    """
    Primary extractor: Uses LLM.
    Calculates duration dynamically using DateParser.
    Verifies extracted entities via text matching / SBERT.
    Falls back to legacy regex extraction if LLM fails.
    """
    llm_data = _get_llm_data(text)
    if not llm_data:
        return _extract_experience_fallback(text, nlp_model)

    llm_exp = llm_data.get("experience", [])
    if not llm_exp:
        return []

    sbert = _get_sbert()
    experiences = []

    for exp in llm_exp:
        if not isinstance(exp, dict): continue
        conf = float(exp.get("confidence", 1.0))
        if conf < 0.60: continue

        company = exp.get("company", "")
        role = exp.get("role", "")
        date_range_str = exp.get("date_range", "")

        verify_str = f"{company} {role}".strip()
        if verify_str and _verify_entity(verify_str, text, sbert, threshold=0.45):
            dur = 0
            if date_range_str:
                parts = re.split(r'[-–to]', date_range_str.lower())
                if len(parts) >= 2:
                    start_str = parts[0].strip()
                    end_str = parts[1].strip()
                    start_date = dateparser.parse(start_str)
                    if 'present' in end_str or 'current' in end_str:
                        end_date = datetime.now()
                    else:
                        end_date = dateparser.parse(end_str)
                    if start_date and end_date:
                        diff = relativedelta(end_date, start_date)
                        dur = max(0, diff.years * 12 + diff.months)

            experiences.append({
                "company": (company or "Unknown Company")[:80],
                "role": (role or "Unknown Role")[:80],
                "duration_months": dur,
                "date_range": date_range_str
            })
        else:
            print(f"[Verification] Dropped hallucinated Experience: {verify_str}")

    return experiences


def _extract_experience_fallback(text: str, nlp_model) -> list:
    """Minimal spaCy NER fallback for Experience."""
    if not nlp_model: return []
    exp_text = _extract_section_text(text, "experience")
    if not exp_text: return []
    doc = nlp_model(exp_text)
    orgs = [ent.text.strip() for ent in doc.ents if ent.label_ == "ORG" and len(ent.text) > 3]
    orgs = list(dict.fromkeys(orgs))
    return [{"company": org, "role": "Unknown", "duration_months": 0, "date_range": "Unknown"} for org in orgs[:3]]


def extract_projects(text: str) -> list:
    """
    Primary extractor: Uses LLM.
    Verifies extracted entities via text matching / SBERT.
    Uses cached domain embeddings (FIX 4).
    Falls back to legacy extraction if LLM fails.
    """
    llm_data = _get_llm_data(text)
    if not llm_data:
        return _extract_projects_fallback(text)

    llm_projects = llm_data.get("projects", [])
    if not llm_projects:
        return []

    sbert = _get_sbert()

    # FIX 4: Use cached domain embeddings (not re-computed each call)
    domain_labels, domain_embeddings = _get_domain_embeddings()

    projects = []
    for p in llm_projects:
        if not isinstance(p, dict): continue
        conf = float(p.get("confidence", 1.0))
        if conf < 0.60: continue

        title = p.get("project", "")
        summary = p.get("summary", "")

        verify_str = f"{title} {summary}".strip()
        if verify_str and _verify_entity(verify_str, text, sbert, threshold=0.45):
            tech_stack = p.get("tech_stack", [])

            full_text = f"{title} {summary} {' '.join(tech_stack)}"
            if len(full_text.strip()) > 5:
                item_emb = sbert.encode([full_text[:400]], convert_to_tensor=True).cpu().numpy()
                dom_scores = cosine_similarity(item_emb, domain_embeddings)[0]
                domain = domain_labels[int(np.argmax(dom_scores))]
            else:
                domain = "General Software"

            projects.append({
                "project": (title or "Unknown Project")[:80],
                "tech_stack": tech_stack,
                "domain": domain,
                "summary": summary[:200] + ("..." if len(summary) >= 200 else "")
            })
        else:
            print(f"[Verification] Dropped hallucinated Project: {title}")

    return projects


def _extract_projects_fallback(text: str) -> list:
    """Regex fallback: scan the Projects section for titled entries."""
    proj_text = _extract_section_text(text, "projects")
    if not proj_text:
        return []
    projects = []
    for line in proj_text.splitlines():
        line = line.strip()
        if not line or len(line) < 5 or len(line) > 120:
            continue
        if line[0].islower() or line.startswith(('-', '•', '*', '–')):
            continue
        if re.match(r'^[\d\W]+$', line):
            continue
        projects.append({
            "project": line[:80],
            "tech_stack": [],
            "domain": "General Software",
            "summary": ""
        })
    return projects[:6]


def extract_certifications(text: str) -> list:
    """
    Primary extractor: Uses LLM.
    Verifies extracted entities via text matching / SBERT.
    Falls back to legacy section-aware regex extraction if LLM fails.
    """
    llm_data = _get_llm_data(text)
    if not llm_data:
        return _extract_certifications_fallback(text)

    llm_certs = llm_data.get("certifications", [])
    if not llm_certs:
        return []

    sbert = _get_sbert()
    certifications = []

    for cert in llm_certs:
        if not isinstance(cert, dict): continue
        conf = float(cert.get("confidence", 1.0))
        if conf < 0.60: continue

        name = cert.get("name", "")

        if name and _verify_entity(name, text, sbert, threshold=0.45):
            certifications.append({
                "name": name[:80],
                "provider": cert.get("provider", "Unknown Provider"),
                "year": str(cert.get("year", "Unknown"))[:10]
            })
        else:
            print(f"[Verification] Dropped hallucinated Certification: {name}")

    return certifications


def _extract_certifications_fallback(text: str) -> list:
    """Regex fallback: scan the Certifications section for certificate names."""
    cert_text = _extract_section_text(text, "certifications")
    if not cert_text:
        return []
    certs = []
    for line in cert_text.splitlines():
        line = line.strip()
        if not line or len(line) < 5 or len(line) > 150:
            continue
        if line.startswith(('-', '•', '*', '–')):
            line = line[1:].strip()
        if not line:
            continue
        if line[0].islower():
            continue
        certs.append({
            "name": line[:80],
            "provider": "Unknown",
            "year": "Unknown"
        })
    return certs[:6]