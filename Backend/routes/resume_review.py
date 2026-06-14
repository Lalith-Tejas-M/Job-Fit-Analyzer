from flask import Blueprint, request, jsonify
import database
import json
from models.resume_reviewer import review_resume

bp = Blueprint('resume_review', __name__)

@bp.route('/review-resume', methods=['POST'])
def handle_review_resume():
    data = request.get_json()
    user_id = data.get('user_id')
    resume_id = data.get('resume_id')
    role_id = data.get('role_id')
    
    if not all([user_id, resume_id, role_id]):
        return jsonify({"error": "Missing required fields"}), 400
        
    resumes = database.query('SELECT parsed_text FROM resumes WHERE resume_id = ?', [resume_id])
    job_roles = database.query('SELECT job_description FROM job_roles WHERE role_id = ?', [role_id])
    
    if not resumes or not job_roles:
        return jsonify({"error": "Resume or job role not found"}), 404
        
    resume_text = resumes[0]['parsed_text']
    job_description = job_roles[0]['job_description']
    
    # 1. Generate feedback via Ollama
    review_data = review_resume(resume_text, job_description)
    
    # 2. Persist feedback
    database.query('''
        UPDATE analysis_history 
        SET review_feedback = ? 
        WHERE user_id = ? AND resume_id = ? AND role_id = ?
    ''', [json.dumps(review_data), user_id, resume_id, role_id])
    
    # 3. Respond
    return jsonify({
        "review": review_data
    }), 200
