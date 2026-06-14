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
# Skill Blacklist — generic English words that are NEVER skills
# =============================================================================
SKILL_BLACKLIST = {
    "learn", "learning", "agent", "project", "projects", "application",
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
# Expanded Canonical Skill Map (Replaced with MASTER_SKILLS for Weakness 2)
# =============================================================================
MASTER_SKILLS = [
    "AWS", "Google Cloud", "Machine Learning", "Deep Learning", "AI", "NLP", 
    "Computer Vision", "Python", "Java", "JavaScript", "TypeScript", "C++", 
    "C#", "Go", "Rust", "PHP", "Ruby", "Swift", "Kotlin", "R", "Scala", 
    "Bash", "NumPy", "Pandas", "Scikit-learn", "TensorFlow", "PyTorch", 
    "Keras", "OpenCV", "HuggingFace", "LangChain", "CrewAI", "LlamaIndex", 
    "NLTK", "spaCy", "Matplotlib", "Seaborn", "XGBoost", "LightGBM", 
    "Flask", "Django", "FastAPI", "Spring Boot", "Express.js", "Node.js", 
    "React", "Angular", "Vue.js", "SQL", "MySQL", "PostgreSQL", "MongoDB", 
    "Redis", "Elasticsearch", "Cassandra", "SQLite", "Docker", "Kubernetes", 
    "Git", "GitHub", "GitLab", "Jenkins", "Ansible", "Terraform", "Azure", 
    "Linux", "Airflow", "Kafka", "Apache Spark", "Hadoop", "Tableau", 
    "Power BI", "REST API", "GraphQL", "Agile", "Scrum", "MLOps", "LLM", "RAG"
]

# =============================================================================
# Multi-word skill phrase scanner
# Scan raw text for known tech phrases BEFORE NER (prevents word fragmentation).
# Ordered longest-first so "Natural Language Processing" matches before "NLP".
# =============================================================================

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


def get_nlp_model():
    """
    Lazy-load spaCy + JobBERT skill NER once and return spaCy model.

    WARNING: HuggingFace pipelines can be slow/memory intensive on first load.
    In production, use ONNX/TensorRT or host the model on a separate GPU microservice.
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
            aggregation_strategy="first",  # merges BIO spans into whole entity
            device=-1,                     # CPU; set to 0 if GPU available
        )
        print("  JobBERT skill NER loaded.")
    return nlp


def _normalize_skill(skill: str) -> str:
    """Map raw skill strings to canonical names using SBERT similarity."""
    global canonical_embeddings
    skill_stripped = skill.strip()
    skill_title = skill_stripped.title()

    # Blacklist check (case-insensitive)
    if skill_stripped.lower() in SKILL_BLACKLIST:
        return ""

    # Exact match fast path
    if skill_title in MASTER_SKILLS or skill_stripped in MASTER_SKILLS:
        return skill_title if skill_title in MASTER_SKILLS else skill_stripped

    # SBERT semantic match against MASTER_SKILLS
    sbert = _get_sbert()
    if canonical_embeddings is None:
        canonical_embeddings = sbert.encode(MASTER_SKILLS, convert_to_tensor=True).cpu().numpy()
        
    skill_emb = sbert.encode([skill_title], convert_to_tensor=True).cpu().numpy()
    scores = cosine_similarity(skill_emb, canonical_embeddings)[0]
    best_idx = int(np.argmax(scores))
    
    if scores[best_idx] > 0.85:
        return MASTER_SKILLS[best_idx]

    return skill_title


_resume_sentences_cache = {}

def _verify_entity(entity: str, text: str, sbert, threshold: float = 0.5) -> bool:
    """
    Verification Layer (Weakness 7):
    Prevents LLM hallucinations by enforcing that the extracted entity
    either exactly matches text in the resume, or semantically matches
    a line in the resume text above a certain threshold.
    """
    if not entity or not text:
        return False
        
    entity_lower = entity.lower()
    text_lower = text.lower()
    
    # 1. Exact Substring Match (Fast Path)
    # Removing punctuation for a more robust text match
    clean_entity = re.sub(r'[^\w\s]', '', entity_lower)
    clean_text = re.sub(r'[^\w\s]', '', text_lower)
    if clean_entity in clean_text:
        return True
        
    # 2. Semantic Match against lines
    import hashlib
    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
    
    global _resume_sentences_cache
    if text_hash not in _resume_sentences_cache:
        # Clear cache for memory safety
        _resume_sentences_cache.clear()
        
        # Split text into chunks (e.g., lines)
        lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 5]
        if not lines:
            return False
            
        # Batch encode all lines
        line_embs = sbert.encode(lines, convert_to_tensor=True).cpu().numpy()
        _resume_sentences_cache[text_hash] = line_embs
        
    line_embs = _resume_sentences_cache[text_hash]
    entity_emb = sbert.encode([entity], convert_to_tensor=True).cpu().numpy()
    
    scores = cosine_similarity(entity_emb, line_embs)[0]
    best_score = float(np.max(scores))
    
    return best_score >= threshold


def _extract_section_text(text: str, section_key: str) -> str:
    """
    Locate a named section in raw resume text using header regex patterns.
    Returns the text block from the section header until the next section header.
    Handles: trailing colons, dashes, mixed case, and extra whitespace.
    """
    target_pattern = SECTION_HEADER_PATTERNS.get(section_key)
    if not target_pattern:
        return ""

    # Find the target section start
    target_match = target_pattern.search(text)
    if not target_match:
        print(f"  [SECTION] '{section_key}' header NOT FOUND in text.")
        return ""

    print(f"  [SECTION] '{section_key}' found at char {target_match.start()}: repr={repr(target_match.group(0)[:40])}")
    section_start = target_match.end()

    # Find the next ANY section header after our target section
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
    Skill Fusion Layer (Weakness 1):
    1. Extracts skills from raw text using JobBERT.
    2. Extracts skills using SBERT noun-chunk scoring.
    3. Extracts structured skills from LLM (filtering by confidence).
    4. Merges all sets and normalizes via SBERT.
    """
    global skill_ner
    fused_skills = set()

    # Get specific skills section to prevent token cutoff
    skills_section = _extract_section_text(text, "skills")
    # We analyze the skills section + top of resume (summaries)
    target_text = (text[:1000] + " " + skills_section)[:3000] if skills_section else text[:3000]

    # ── Step 1: JobBERT Extraction on RAW Text ───────────────────────────────
    if skill_ner:
        try:
            # Chunk the text to prevent HuggingFace token limits (max 512) and scan the entire resume
            chunks = [text[i:i+2500] for i in range(0, len(text), 2500)]
            for chunk in chunks:
                ner_results = skill_ner(chunk)
                for ent in ner_results:
                    if ent.get("score", 0) >= 0.50:  # Lowered threshold for better recall
                        word = ent["word"].replace("##", "").strip()
                        if len(word) >= 2 and not word.isnumeric() and len(word.split()) <= 4:
                            fused_skills.add(word)
        except Exception as e:
            print(f"[JobBERT NER] Error: {e}")

    # ── Step 1.5: SBERT Noun-Chunk Scoring (Supplementary) ───────────────────
    if nlp_model:
        sbert = _get_sbert()
        doc = nlp_model(text)
        skill_anchors = _get_skill_anchors()
        for chunk in doc.noun_chunks:
            candidate = chunk.text.replace('\n', ' ').strip()
            words = candidate.split()
            if not (1 <= len(words) <= 3):
                continue
            if candidate.lower() in SKILL_BLACKLIST:
                continue
            chunk_emb = sbert.encode([candidate], convert_to_tensor=True).cpu().numpy()
            score = float(np.max(cosine_similarity(chunk_emb, skill_anchors)))
            if score > 0.60:
                fused_skills.add(candidate)

    # ── Step 2: LLM Extraction & Confidence Filtering (Weakness 8) ───────────
    llm_data = _get_llm_data(text)
    if llm_data and "skills" in llm_data:
        for sk_obj in llm_data.get("skills", []):
            if isinstance(sk_obj, dict):
                skill_name = sk_obj.get("skill", "")
                conf = float(sk_obj.get("confidence", 1.0))
                if conf >= 0.60 and skill_name and len(skill_name.split()) <= 4:
                    fused_skills.add(skill_name)
            elif isinstance(sk_obj, str) and len(sk_obj.split()) <= 4:
                fused_skills.add(sk_obj)

    # Fallback if ALL fail
    if not fused_skills and not llm_data:
        return _extract_skills_fallback(text, nlp_model)

    # ── Step 3: SBERT Normalization ──────────────────────────────────────────
    normalized = []
    for s in fused_skills:
        norm = _normalize_skill(s)
        if norm and norm.lower() not in SKILL_BLACKLIST:
            normalized.append(norm)

    return list(set(normalized))


def _extract_skills_fallback(text: str, nlp_model) -> list:
    """
    Extract skills using a model-first pipeline:

    Step 1 — JobBERT skill NER (primary extractor)
        Model:  jjzha/jobbert_skill_extraction
        Trained on 3.2M job postings; outputs B-SKILL/I-SKILL BIO tags.
        aggregation_strategy='first' produces correct multi-word spans:
            'Natural Language Processing' → one SKILL entity  ✓
            'Scikit-learn' → one SKILL entity  ✓
            'PyTorch' → one SKILL entity  ✓
        Confidence threshold: 0.70 (tune lower to increase recall).

    Step 2 — SBERT noun-chunk scoring (supplementary)
        Catches skills the NER might miss (novel frameworks, acronyms).
        Uses cached anchor embeddings — no re-encoding per call.

    Step 3 — Normalize + deduplicate
        CANONICAL_SKILLS maps spelling variants to canonical names.
        SKILL_BLACKLIST removes generic non-skill words.
    """
    global skill_ner
    skills_found = set()
    sbert = _get_sbert()

    # Get specific skills section to prevent token cutoff
    skills_section = _extract_section_text(text, "skills")
    target_text = (text[:1000] + " " + skills_section)[:3000] if skills_section else text[:3000]

    # ── Step 1: JobBERT — domain-adapted skill NER ────────────────────────────
    if skill_ner:
        try:
            ner_results = skill_ner(target_text)
            for ent in ner_results:
                # Only accept entities the model is confident about
                if ent.get("score", 0) < 0.50:
                    continue
                # Entity group from jobbert is 'SKILL' (B-SKILL merged)
                word = ent["word"].replace("##", "").strip()
                if len(word) >= 3 and not word.isnumeric() and len(word.split()) <= 4:
                    skills_found.add(word)
        except Exception as e:
            print(f"[Fallback JobBERT NER] Error: {e}")

    # ── Step 2: SBERT noun-chunk scoring (supplementary catch-all) ───────────
    if nlp_model:
        doc = nlp_model(text[:3000])
        skill_anchors = _get_skill_anchors()  # cached — not re-encoded per call
        for chunk in doc.noun_chunks:
            candidate = chunk.text.replace('\n', ' ').strip()
            words = candidate.split()
            if not (1 <= len(words) <= 3):
                continue
            if candidate.lower() in SKILL_BLACKLIST:
                continue
            chunk_emb = sbert.encode([candidate], convert_to_tensor=True).cpu().numpy()
            score = float(np.max(cosine_similarity(chunk_emb, skill_anchors)))
            if score > 0.60:
                skills_found.add(candidate)

    # ── Step 3: Normalize + deduplicate ───────────────────────────────────
    normalized = []
    for s in skills_found:
        norm = _normalize_skill(s)
        if norm and norm.lower() not in SKILL_BLACKLIST:
            normalized.append(norm)

    return list(set(normalized))



def extract_education(text: str, nlp_model) -> list:
    """
    Primary extractor: Uses LLM.
    Verifies extracted entities via text matching / SBERT (Weakness 3).
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
        
        # Verification Layer (Weakness 3 & 7)
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
    """Minimal spaCy NER fallback for Education (Weakness 9)."""
    if not nlp_model: return []
    doc = nlp_model(text[:3000])
    orgs = [ent.text.strip() for ent in doc.ents if ent.label_ == "ORG" and len(ent.text) > 3]
    return [{"degree": "Unknown", "branch": "Unknown", "university": org, "year": "Unknown"} for org in orgs[:2]]


def extract_experience(text: str, nlp_model) -> list:
    """
    Primary extractor: Uses LLM.
    Calculates duration dynamically using DateParser (Weakness 4).
    Verifies extracted entities via text matching / SBERT (Weakness 7).
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
        
        # Verification Layer (Weakness 7)
        verify_str = f"{company} {role}".strip()
        if verify_str and _verify_entity(verify_str, text, sbert, threshold=0.45):
            
            # DateParser logic for duration (Weakness 4)
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
    """Minimal spaCy NER fallback for Experience (Weakness 9)."""
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
    Verifies extracted entities via text matching / SBERT (Weakness 7).
    Preserves SBERT domain classification on the LLM output.
    Falls back to legacy extraction if LLM fails.
    """
    llm_data = _get_llm_data(text)
    if not llm_data:
        return _extract_projects_fallback(text)

    llm_projects = llm_data.get("projects", [])
    if not llm_projects:
        return []

    sbert = _get_sbert()
    domain_labels = [
        "Web Development",
        "AI and Machine Learning",
        "Data Science and Analytics",
        "DevOps and Cloud",
        "Mobile App Development",
        "Cybersecurity",
        "General Software"
    ]
    domain_embeddings = sbert.encode(domain_labels, convert_to_tensor=True).cpu().numpy()

    projects = []
    for p in llm_projects:
        if not isinstance(p, dict): continue
        conf = float(p.get("confidence", 1.0))
        if conf < 0.60: continue

        title = p.get("project", "")
        summary = p.get("summary", "")
        
        # Verification Layer (Weakness 7)
        verify_str = f"{title} {summary}".strip()
        if verify_str and _verify_entity(verify_str, text, sbert, threshold=0.45):
            tech_stack = p.get("tech_stack", [])
            
            # SBERT domain classification
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
    # Each line starting with a capital letter likely marks a project title
    for line in proj_text.splitlines():
        line = line.strip()
        if not line or len(line) < 5 or len(line) > 120:
            continue
        # Skip lines that look like bullet content (start with verb or lower case)
        if line[0].islower() or line.startswith(('-', '•', '*', '–')):
            continue
        # Skip lines that are purely punctuation / numbers
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
    Verifies extracted entities via text matching / SBERT (Weakness 6 & 7).
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
        
        # Verification Layer (Weakness 6 & 7)
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
        # Skip lines that are purely lower-case content sentences
        if line[0].islower():
            continue
        certs.append({
            "name": line[:80],
            "provider": "Unknown",
            "year": "Unknown"
        })
    return certs[:6]