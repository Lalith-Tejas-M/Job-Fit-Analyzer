# backend/routes/analysis.py
from flask import Blueprint, request, jsonify
import uuid
import database
import base64
from models.embeddings import get_embedding_from_bytes, model as embed_model
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from models.nlp_processor import extract_skills, get_nlp_model
import json

# Recommendations powered by Ollama (Llama 3) + live YouTube search via yt-dlp
from models.recomendor import generate_recommendations


def perform_semantic_skill_match(required_skills, candidate_skills):
    """Checks if required skills exist in candidate skills semantically"""
    if not required_skills:
        return [], []
    if not candidate_skills:
        return [], required_skills
        
    req_embs = embed_model.encode(required_skills, convert_to_tensor=True).cpu().numpy()
    can_embs = embed_model.encode(candidate_skills, convert_to_tensor=True).cpu().numpy()
    
    sim_matrix = cosine_similarity(req_embs, can_embs)
    
    matched = []
    missing = []

    for i, req in enumerate(required_skills):
        max_sim = np.max(sim_matrix[i]) if len(candidate_skills) > 0 else 0
        if max_sim >= 0.65:   # Lowered from 0.75 — was too strict for normalized skill names
            matched.append(req)
        else:
            missing.append(req)

    return matched, missing

def calculate_hybrid_score(resume, job_embedding, required_skills, matched_skills):
    """
    Calculates a decomposed ATS score with graduated (not binary) sub-scores.
    """
    # ------------------------------------------------------------------
    # 1. Semantic Score (40%) — cosine similarity of full resume vs JD
    # ------------------------------------------------------------------
    resume_embedding_bytes = base64.b64decode(resume['resume_embedding'])
    resume_embedding = get_embedding_from_bytes(resume_embedding_bytes)

    semantic_score = float(cosine_similarity(
        resume_embedding.reshape(1, -1),
        job_embedding.reshape(1, -1)
    )[0][0]) * 100
    semantic_score = max(0.0, min(100.0, semantic_score))

    # ------------------------------------------------------------------
    # 2. Skill Score (25%) — % of required skills matched
    # ------------------------------------------------------------------
    skill_score = (len(matched_skills) / len(required_skills) * 100) if required_skills else 100.0

    # ------------------------------------------------------------------
    # 3. Experience Score (15%) — graduated by total experience months
    #    Benchmarks: 3 mo = 25, 6 mo = 50, 12 mo = 75, 24+ mo = 100
    # ------------------------------------------------------------------
    exp_details = json.loads(resume.get('experience_details') or '[]')
    total_months = sum(e.get('duration_months', 0) for e in exp_details)
    if total_months == 0:
        experience_score = 0.0
    elif total_months <= 3:
        experience_score = 25.0
    elif total_months <= 6:
        experience_score = 50.0
    elif total_months <= 12:
        experience_score = 70.0
    elif total_months <= 24:
        experience_score = 85.0
    else:
        experience_score = 100.0

    # ------------------------------------------------------------------
    # 4. Project Score (10%) — graduated by count + tech stack relevance
    #    Base: 0 proj=0, 1 proj=40, 2 proj=65, 3 proj=80, 4+ proj=100
    #    Bonus: up to +15 if project tech matches required skills
    # ------------------------------------------------------------------
    projects = json.loads(resume.get('projects') or '[]')
    proj_count = len(projects)
    if proj_count == 0:
        base_project_score = 0.0
    elif proj_count == 1:
        base_project_score = 40.0
    elif proj_count == 2:
        base_project_score = 65.0
    elif proj_count == 3:
        base_project_score = 80.0
    else:
        base_project_score = 100.0

    # Relevance bonus: check how many required skills appear in project tech stacks
    all_proj_techs = set()
    for p in projects:
        for t in p.get('tech_stack', []):
            all_proj_techs.add(t.lower())
    if required_skills and all_proj_techs:
        matched_in_proj = sum(
            1 for s in required_skills if s.lower() in all_proj_techs
        )
        relevance_bonus = min(15.0, (matched_in_proj / len(required_skills)) * 15)
    else:
        relevance_bonus = 0.0

    project_score = min(100.0, base_project_score + relevance_bonus)

    # ------------------------------------------------------------------
    # 5. Education Score (5%) — graduated by completeness of entries
    #    0 entries=0, 1 basic entry=50, 1 complete entry=80, 2+ entries=100
    # ------------------------------------------------------------------
    education = json.loads(resume.get('education_details') or '[]')
    edu_count = len(education)
    if edu_count == 0:
        education_score = 0.0
    elif edu_count == 1:
        ed = education[0]
        # Count how many fields are meaningfully filled
        complete_fields = sum([
            ed.get('degree', 'Unknown Degree') != 'Unknown Degree',
            ed.get('university', 'Unknown University') != 'Unknown University',
            ed.get('branch', 'Unknown Branch') != 'Unknown Branch',
            ed.get('year', 'Unknown') != 'Unknown',
        ])
        if complete_fields >= 3:
            education_score = 80.0
        elif complete_fields >= 2:
            education_score = 60.0
        else:
            education_score = 40.0
    else:
        education_score = 100.0

    # ------------------------------------------------------------------
    # 6. Certification Score (5%) — graduated by count
    #    0=0, 1=60, 2=80, 3+=100
    # ------------------------------------------------------------------
    certs = json.loads(resume.get('certifications') or '[]')
    cert_count = len(certs)
    if cert_count == 0:
        cert_score = 0.0
    elif cert_count == 1:
        cert_score = 60.0
    elif cert_count == 2:
        cert_score = 80.0
    else:
        cert_score = 100.0

    # ------------------------------------------------------------------
    # Weighted overall score
    # ------------------------------------------------------------------
    overall_score = (
        0.40 * semantic_score +
        0.25 * skill_score +
        0.15 * experience_score +
        0.10 * project_score +
        0.05 * education_score +
        0.05 * cert_score
    )

    return {
        "semantic_score":    round(semantic_score, 1),
        "skill_score":       round(skill_score, 1),
        "experience_score":  round(experience_score, 1),
        "project_score":     round(project_score, 1),
        "education_score":   round(education_score, 1),
        "cert_score":        round(cert_score, 1),
        "overall_score":     round(overall_score, 1)
    }


bp = Blueprint('analysis', __name__)


@bp.route('/job-roles', methods=['GET'])
def get_job_roles():
    roles = database.query('SELECT role_id, role_name, industry FROM job_roles')
    return jsonify({
        "roles": [{"role_id": r['role_id'], "role_name": r['role_name'], "industry": r['industry']}
                  for r in roles]
    }), 200


@bp.route('/analyze-role', methods=['POST'])
def analyze_role():
    data = request.get_json()
    user_id   = data.get('user_id')
    resume_id = data.get('resume_id')
    role_id   = data.get('role_id')

    if not all([user_id, resume_id, role_id]):
        return jsonify({"error": "Missing required fields"}), 400

    resumes = database.query('SELECT resume_embedding, skills, experience_details, projects, education_details, certifications FROM resumes WHERE resume_id = ?', [resume_id])
    job_roles = database.query('SELECT role_name, job_description, required_skills, jd_embedding FROM job_roles WHERE role_id = ?', [role_id])
    
    if not resumes or not job_roles:
        return jsonify({"error": "Resume or job role not found"}), 404
        
    resume = resumes[0]
    job_role = job_roles[0]

    if not job_role['jd_embedding']:
        from models.embeddings import generate_embedding
        jd_blob = generate_embedding(job_role['job_description'])
        jd_b64 = base64.b64encode(jd_blob).decode('utf-8')
        database.query('UPDATE job_roles SET jd_embedding = ? WHERE role_id = ?', [jd_b64, role_id])
        job_embedding = get_embedding_from_bytes(jd_blob)
    else:
        jd_blob = base64.b64decode(job_role['jd_embedding'])
        job_embedding = get_embedding_from_bytes(jd_blob)

    # ---- semantic skill gap ----
    candidate_skills = list(set(json.loads(resume['skills'])))
    required_skills  = list(set(json.loads(job_role['required_skills'])))
    matched_skills, missing_skills = perform_semantic_skill_match(required_skills, candidate_skills)

    # ---- hybrid score ----
    scores = calculate_hybrid_score(resume, job_embedding, required_skills, matched_skills)

    # ========== ATS DEBUG ==========
    print("\n" + "=" * 40)
    print("  ATS DEBUG (/analyze-role)")
    print("=" * 40)
    print(f"  Candidate Skills : {candidate_skills}")
    print(f"  Required Skills  : {required_skills}")
    print(f"  Matched Skills   : {matched_skills}")
    print(f"  Missing Skills   : {missing_skills}")
    print(f"  Scores           : {scores}")
    print("=" * 40 + "\n")

    # ---- rich roadmap ----
    recommendations = generate_recommendations(missing_skills, scores['overall_score'], resume=resume, job_context=job_role['job_description'])

    # ---- persist ----
    analysis_id = database.generate_id()
    database.query('''
        INSERT INTO analysis_history (analysis_id, user_id, resume_id, role_id,
                                    job_match_score, missing_skills, recommendations,
                                    semantic_score, skill_score, experience_score, project_score, education_score, cert_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        analysis_id, user_id, resume_id, role_id,
        scores['overall_score'], json.dumps(missing_skills), json.dumps(recommendations),
        scores['semantic_score'], scores['skill_score'], scores['experience_score'], scores['project_score'], scores['education_score'], scores['cert_score']
    ])

    # ---- response ----
    return jsonify({
        "analysis_id": analysis_id,
        "job_match_score": scores['overall_score'],
        "role_name": job_role['role_name'],
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "recommendations": recommendations,
        "scores": scores
    }), 200


@bp.route('/analysis/latest', methods=['GET'])
def get_latest_analysis():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "User ID required"}), 400

    rows = database.query('''
        SELECT ah.*, jr.role_name
        FROM analysis_history ah
        JOIN job_roles jr ON ah.role_id = jr.role_id
        WHERE ah.user_id = ?
        ORDER BY ah.timestamp DESC
        LIMIT 1
    ''', [user_id])
    
    if not rows:
        return jsonify({"error": "No analysis found"}), 404
        
    latest = rows[0]

    return jsonify({
        "analysis_id": latest['analysis_id'],
        "job_match_score": latest['job_match_score'],
        "role_name": latest['role_name'],
        "missing_skills": json.loads(latest['missing_skills']),
        "recommendations": json.loads(latest['recommendations']),
        "scores": {
            "semantic_score": latest.get('semantic_score'),
            "skill_score": latest.get('skill_score'),
            "experience_score": latest.get('experience_score'),
            "project_score": latest.get('project_score'),
            "education_score": latest.get('education_score'),
            "cert_score": latest.get('cert_score'),
            "overall_score": latest.get('job_match_score')
        },
        "timestamp": latest['timestamp']
    }), 200


# ------------------------------------------------------------------
#  NEW: analyse free-text job description (no DB row needed)
# ------------------------------------------------------------------
from models.embeddings import generate_embedding, model as embed_model
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

@bp.route('/analyze-text', methods=['POST'])
def analyze_text():
    """
    Expects: { user_id, resume_id, job_description: "free text..." }
    Returns: same JSON shape as /analyze-role
    """
    data = request.get_json()
    user_id   = data.get('user_id')
    resume_id = data.get('resume_id')
    job_text  = data.get('job_description', '').strip()

    if not all([user_id, resume_id, job_text]):
        return jsonify({"error": "Missing fields"}), 400

    resumes = database.query('SELECT resume_embedding, skills, experience_details, projects, education_details, certifications FROM resumes WHERE resume_id = ?', [resume_id])
    if not resumes:
        return jsonify({"error": "Resume not found"}), 404
        
    resume = resumes[0]

    job_embedding = embed_model.encode(job_text, convert_to_tensor=True).cpu().numpy()

    # ---- semantic skill gap vs free text ----
    candidate_skills = list(set(json.loads(resume['skills'])))
    nlp = get_nlp_model()
    required_skills  = list(set(extract_skills(job_text, nlp)))
    matched_skills, missing_skills = perform_semantic_skill_match(required_skills, candidate_skills)

    # ---- hybrid score ----
    scores = calculate_hybrid_score(resume, job_embedding, required_skills, matched_skills)

    # ========== ATS DEBUG ==========
    print("\n" + "=" * 40)
    print("  ATS DEBUG (/analyze-text)")
    print("=" * 40)
    print(f"  Candidate Skills : {candidate_skills}")
    print(f"  Required Skills  : {required_skills}")
    print(f"  Matched Skills   : {matched_skills}")
    print(f"  Missing Skills   : {missing_skills}")
    print(f"  Scores           : {scores}")
    print("=" * 40 + "\n")

    # ---- recommendations ----
    recommendations = generate_recommendations(missing_skills, scores['overall_score'], resume=resume, job_context=job_text)

    # ---- persist to analysis_history ----
    analysis_id = database.generate_id()
    # Use a placeholder role_id for free-text analyses (no DB job_roles row needed)
    free_text_role_id = 'free-text-analysis'
    
    # Ensure the placeholder role exists so FK constraints don't block the insert
    existing = database.query('SELECT role_id FROM job_roles WHERE role_id = ?', [free_text_role_id])
    if not existing:
        database.query(
            'INSERT INTO job_roles (role_id, role_name, industry, job_description, required_skills) VALUES (?, ?, ?, ?, ?)',
            [free_text_role_id, 'Custom Job Description', 'General', job_text[:500], json.dumps(required_skills)]
        )
    
    database.query('''
        INSERT INTO analysis_history (analysis_id, user_id, resume_id, role_id,
                                    job_match_score, missing_skills, recommendations,
                                    semantic_score, skill_score, experience_score, project_score, education_score, cert_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        analysis_id, user_id, resume_id, free_text_role_id,
        scores['overall_score'], json.dumps(missing_skills), json.dumps(recommendations),
        scores['semantic_score'], scores['skill_score'], scores['experience_score'],
        scores['project_score'], scores['education_score'], scores['cert_score']
    ])

    return jsonify({
        "analysis_id": analysis_id,
        "job_match_score": scores['overall_score'],
        "role_name": "Custom Job Description",
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "recommendations": recommendations,
        "scores": scores
    }), 200