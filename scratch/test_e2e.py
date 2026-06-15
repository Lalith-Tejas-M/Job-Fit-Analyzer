import requests
import time
import os
import json

BASE_URL = "http://localhost:5000/api"

def run_test():
    print("=== STARTING END-TO-END EFFICIENT INTEGRATION TEST ===")
    
    # 1. Register or login user
    user_email = "test_user_e2e@example.com"
    user_password = "password123"
    
    login_data = {
        "email": user_email,
        "password": user_password
    }
    
    print("Attempting login...")
    resp = requests.post(f"{BASE_URL}/login", json=login_data)
    if resp.status_code == 200:
        user_id = resp.json()["user_id"]
        print(f"Logged in user: {user_id}")
    else:
        print("Login failed, attempting register...")
        reg_data = {
            "name": "E2E Test User",
            "email": user_email,
            "password": user_password
        }
        resp = requests.post(f"{BASE_URL}/register", json=reg_data)
        if resp.status_code == 201:
            user_id = resp.json()["user_id"]
            print(f"Registered user: {user_id}")
        else:
            print(f"Registration failed: {resp.text}")
            return
            
    # 2. Upload resume
    pdf_filename = "06f4a862-c3ed-4a3e-b962-1e09d980a627_Lalith-3pdf.pdf"
    pdf_path = os.path.join("uploads", pdf_filename)
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found.")
        return
        
    print(f"Uploading and processing resume '{pdf_filename}'...")
    start_time = time.time()
    with open(pdf_path, "rb") as f:
        files = {"file": (pdf_filename, f, "application/pdf")}
        data = {"user_id": user_id}
        resp = requests.post(f"{BASE_URL}/upload-resume", files=files, data=data)
        
    upload_duration = time.time() - start_time
    print(f"Upload and processing finished in {upload_duration:.2f} seconds.")
    
    if resp.status_code != 201:
        print(f"Upload failed: {resp.text}")
        return
        
    upload_res = resp.json()
    resume_id = upload_res["resume_id"]
    extracted_skills = upload_res["skills"]
    print(f"Successfully processed resume. ID: {resume_id}")
    print(f"Extracted skills count: {len(extracted_skills)}")
    print(f"Extracted skills: {extracted_skills}")
    
    # 3. Check for sentence fragments/project titles in extracted skills (Fix 1 verification)
    sentence_like = [s for s in extracted_skills if len(s.split()) > 3 or any(w in s.lower() for w in ["powered", "based", "driven", "intelligent"])]
    if sentence_like:
        print(f"WARNING: Extracted skills contains sentence/project fragments: {sentence_like}")
    else:
        print("Success: No sentence fragments or project titles leaked into the skills list.")
        
    # 4. Get job roles
    print("Fetching job roles...")
    resp = requests.get(f"{BASE_URL}/job-roles")
    if resp.status_code != 200:
        print(f"Failed to fetch job roles: {resp.text}")
        return
        
    roles = resp.json()["roles"]
    print(f"Found {len(roles)} job roles.")
    ml_role = next((r for r in roles if "Machine Learning" in r["role_name"]), None)
    if not ml_role:
        ml_role = roles[0]
        
    role_id = ml_role["role_id"]
    role_name = ml_role["role_name"]
    print(f"Selected job role for analysis: '{role_name}' (ID: {role_id})")
    
    # 5. Run Job Fit Analysis & Roadmap Generation (Fix 3 & 4 verification)
    print("Running analysis & roadmap generation...")
    analysis_start = time.time()
    analysis_data = {
        "user_id": user_id,
        "resume_id": resume_id,
        "role_id": role_id
    }
    resp = requests.post(f"{BASE_URL}/analyze-role", json=analysis_data)
    analysis_duration = time.time() - analysis_start
    print(f"Analysis completed in {analysis_duration:.2f} seconds.")
    
    if resp.status_code != 200:
        print(f"Analysis failed: {resp.text}")
        return
        
    analysis_res = resp.json()
    match_score = analysis_res["job_match_score"]
    missing_skills = analysis_res["missing_skills"]
    recommendations = analysis_res["recommendations"]
    
    print(f"Job Match Score: {match_score}%")
    print(f"Missing Skills: {missing_skills}")
    
    # 6. Verify Roadmap structure (Fix 3 verification)
    print("\n--- ROADMAP STRUCTURE VERIFICATION ---")
    short_term = recommendations.get("short_term", [])
    print(f"Short term roadmap length: {len(short_term)}")
    for item in short_term:
        print(f"\nSkill: {item['skill']}")
        print(f"  Estimated Hours: {item.get('hours')}h")
        print(f"  Steps: {item.get('steps')}")
        print(f"  Project Idea: {item.get('project')}")
        print(f"  Certificate: {item.get('certificate')}")
        
        resources = item.get("resources", [])
        types = [r.get("type") for r in resources]
        print(f"  Resource types available: {types}")
        
        # Check that we have curated resources beyond just video
        non_video = [t for t in types if t != 'video']
        if non_video:
            print("  Success: Rich resources (docs/courses/practice) exist.")
        else:
            print("  WARNING: Only video resources found.")
            
    print("\n=======================================================")
    print(f"TOTAL ROUND TRIP TIME: {upload_duration + analysis_duration:.2f} seconds.")
    print("=======================================================")

if __name__ == "__main__":
    run_test()
