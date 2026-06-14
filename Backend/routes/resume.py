from flask import Blueprint, request, jsonify
import json
import pdfplumber
import uuid
import database
import base64
from models.nlp_processor import extract_skills, extract_education, extract_experience, extract_projects, extract_certifications, get_nlp_model
from models.embeddings import generate_embedding
import os

# Inline PDF parser
def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file"""
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return ""
    return text.strip()

bp = Blueprint('resume', __name__)

@bp.route('/upload-resume', methods=['POST'])
def upload_resume():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    user_id = request.form.get('user_id')
    
    if not user_id:
        return jsonify({"error": "User ID required"}), 400
    
    if not file.filename.endswith('.pdf'):
        return jsonify({"error": "Only PDF files allowed"}), 400
    
    # Save file
    filename = f"{user_id}_{file.filename}"
    filepath = os.path.join('uploads', filename)
    file.save(filepath)
    
    # Extract text
    text = extract_text_from_pdf(filepath)
    if not text:
        os.remove(filepath)
        return jsonify({"error": "Could not extract text from PDF"}), 400
    
    # Process with NLP
    nlp = get_nlp_model()
    skills = extract_skills(text, nlp)
    education = extract_education(text, nlp)
    experience = extract_experience(text, nlp)
    projects = extract_projects(text)
    certifications = extract_certifications(text)
    
    # ========== NLP EXTRACTION DEBUG ==========
    print("\n" + "=" * 45)
    print("  NLP EXTRACTION RESULTS")
    print("=" * 45)
    print(f"  SKILLS       ({len(skills)}): {skills}")
    print(f"  EDUCATION    ({len(education)}): {json.dumps(education, indent=2)}")
    print(f"  EXPERIENCE   ({len(experience)}): {json.dumps(experience, indent=2)}")
    print(f"  PROJECTS     ({len(projects)}): {json.dumps(projects, indent=2)}")
    print(f"  CERTS        ({len(certifications)}): {json.dumps(certifications, indent=2)}")
    print("=" * 45 + "\n")

    # Generate embedding
    embedding_blob = generate_embedding(text)

    resume_id = database.generate_id()
    embedding_b64 = base64.b64encode(embedding_blob).decode('utf-8')

    database.query('''
        INSERT INTO resumes (resume_id, user_id, file_name, file_path, parsed_text,
                           skills, education, experience, resume_embedding,
                           certifications, projects, experience_details, education_details)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        resume_id, user_id, filename, filepath, text,
        json.dumps(skills), json.dumps(education), json.dumps(experience),
        embedding_b64,
        json.dumps(certifications), json.dumps(projects), json.dumps(experience), json.dumps(education)
    ])

    return jsonify({
        "message": "Resume uploaded and processed",
        "resume_id": resume_id,
        "skills": skills,
        "skill_count": len(skills),
        "experience_count": len(experience),
        "project_count": len(projects),
        "cert_count": len(certifications)
    }), 201


@bp.route('/debug-resume/<resume_id>', methods=['GET'])
def debug_resume(resume_id):
    """
    Diagnostic endpoint: re-run NLP extraction on an already-stored resume
    and return exactly what each extractor sees.
    GET /api/debug-resume/<resume_id>
    """
    rows = database.query(
        'SELECT parsed_text FROM resumes WHERE resume_id = ?', [resume_id]
    )
    if not rows:
        return jsonify({"error": "Resume not found"}), 404

    text = rows[0].get('parsed_text', '')
    if not text:
        return jsonify({"error": "parsed_text is empty"}), 400

    # Show the raw first 2000 chars so you can see pdfplumber output
    raw_preview = text[:2000]

    # Find which section headers exist in the text
    from models.nlp_processor import (
        SECTION_HEADER_PATTERNS, _HEADER_LINE_RE,
        get_nlp_model, extract_skills, extract_education,
        extract_experience, extract_projects, extract_certifications,
        _extract_section_text
    )

    headers_found = {}
    for key, pat in SECTION_HEADER_PATTERNS.items():
        m = pat.search(text)
        headers_found[key] = repr(m.group(0).strip()) if m else None

    nlp = get_nlp_model()
    skills        = extract_skills(text, nlp)
    education     = extract_education(text, nlp)
    experience    = extract_experience(text, nlp)
    projects      = extract_projects(text)
    certifications = extract_certifications(text)

    return jsonify({
        "raw_text_preview": raw_preview,
        "section_headers_detected": headers_found,
        "skills":         skills,
        "education":      education,
        "experience":     experience,
        "projects":       projects,
        "certifications": certifications,
        "counts": {
            "skills":         len(skills),
            "education":      len(education),
            "experience":     len(experience),
            "projects":       len(projects),
            "certifications": len(certifications),
        }
    }), 200