# backend/database.py
import os
import json
import uuid
import requests
from datetime import datetime

FLUXBASE_API_KEY = "fl_5004aeadc7878f6bfb50e9c93f2302af62d0a8cae71c3d65"
FLUXBASE_PROJECT_ID = "46cc93f415ee43de"
FLUXBASE_URL = "https://fluxbase.vercel.app/api/execute-sql"

def query(sql, params=None):
    if params is None:
        params = []
    
    payload = {
        "projectId": FLUXBASE_PROJECT_ID,
        "query": sql,
        "params": params
    }
    
    headers = {
        "Authorization": f"Bearer {FLUXBASE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(FLUXBASE_URL, json=payload, headers=headers)
    
    try:
        data = response.json()
    except Exception:
        raise Exception(f"Fluxbase returned {response.status_code}: {response.text}")
        
    if not data.get("success"):
        raise Exception(f"Database query failed: {data.get('error', {}).get('message')} - Details: {data.get('error', {}).get('details')}")
        
    return data.get("result", {}).get("rows", [])

def generate_id():
    return str(uuid.uuid4())

def init_db():
    print("Initializing Fluxbase tables...")
    
    def add_column_if_not_exists(table, col_def):
        try:
            query(f"ALTER TABLE {table} ADD COLUMN {col_def}")
            print(f"Added column {col_def} to {table}")
        except Exception as e:
            pass # Ignore if column already exists
    # ----------  tables  ----------
    # Use VARCHAR(255) instead of TEXT for keys/indexes to satisfy MySQL requirements
    query('''
        CREATE TABLE IF NOT EXISTS users (
            user_id VARCHAR(255) PRIMARY KEY,
            name TEXT NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    query('''
        CREATE TABLE IF NOT EXISTS resumes (
            resume_id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            parsed_text TEXT,
            skills TEXT,
            education TEXT,
            experience TEXT,
            resume_embedding TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')

    query('''
        CREATE TABLE IF NOT EXISTS job_roles (
            role_id VARCHAR(255) PRIMARY KEY,
            role_name VARCHAR(255) UNIQUE NOT NULL,
            job_description TEXT NOT NULL,
            required_skills TEXT,
            jd_embedding TEXT,
            industry TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    query('''
        CREATE TABLE IF NOT EXISTS analysis_history (
            analysis_id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            resume_id VARCHAR(255) NOT NULL,
            role_id VARCHAR(255) NOT NULL,
            job_match_score FLOAT NOT NULL,
            missing_skills TEXT,
            recommendations TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (resume_id) REFERENCES resumes(resume_id) ON DELETE CASCADE,
            FOREIGN KEY (role_id) REFERENCES job_roles(role_id) ON DELETE CASCADE
        )
    ''')

    # ---------- schema updates ----------
    # Resumes table
    add_column_if_not_exists("resumes", "certifications TEXT")
    add_column_if_not_exists("resumes", "projects TEXT")
    add_column_if_not_exists("resumes", "experience_details TEXT")
    add_column_if_not_exists("resumes", "education_details TEXT")
    add_column_if_not_exists("resumes", "semantic_score FLOAT")
    add_column_if_not_exists("resumes", "skill_score FLOAT")

    # Analysis History table
    add_column_if_not_exists("analysis_history", "semantic_score FLOAT")
    add_column_if_not_exists("analysis_history", "skill_score FLOAT")
    add_column_if_not_exists("analysis_history", "experience_score FLOAT")
    add_column_if_not_exists("analysis_history", "project_score FLOAT")
    add_column_if_not_exists("analysis_history", "education_score FLOAT")
    add_column_if_not_exists("analysis_history", "cert_score FLOAT")
    add_column_if_not_exists("analysis_history", "review_feedback TEXT")

    # ----------  indexes  ----------
    try:
        query('CREATE INDEX idx_users_email ON users(email)')
    except Exception:
        pass
    try:
        query('CREATE INDEX idx_resumes_user_id ON resumes(user_id)')
    except Exception:
        pass
    try:
        query('CREATE INDEX idx_analysis_history_user_id ON analysis_history(user_id)')
    except Exception:
        pass

    # ----------  16-role seed  ----------
    try:
        rows = query('SELECT COUNT(*) as count FROM job_roles')
        count = int(rows[0]['count']) if rows else 0
    except Exception as e:
        print(f"Could not count job_roles: {e}")
        count = 0
        
    if count == 0:
        default_roles = [
            {
                'role_id': str(uuid.uuid4()),
                'role_name': 'Software Developer',
                'job_description': 'Design, code, test and maintain software applications across the full SDLC.',
                'required_skills': json.dumps(['Python', 'JavaScript', 'Git', 'SQL', 'Algorithms']),
                'industry': 'Tech'
            },
            {
                'role_id': str(uuid.uuid4()),
                'role_name': 'Data Analyst',
                'job_description': 'Collect, clean and interpret data to drive business decisions.',
                'required_skills': json.dumps(['SQL', 'Excel', 'Pandas', 'Tableau', 'Statistics']),
                'industry': 'Tech'
            },
            {
                'role_id': str(uuid.uuid4()),
                'role_name': 'Machine Learning Engineer',
                'job_description': 'Build, train and deploy ML models at scale.',
                'required_skills': json.dumps(['Python', 'Machine Learning', 'TensorFlow', 'Scikit-learn', 'Docker']),
                'industry': 'Tech'
            },
            {
                'role_id': str(uuid.uuid4()),
                'role_name': 'Cloud Engineer',
                'job_description': 'Design, implement and manage cloud infrastructure and services.',
                'required_skills': json.dumps(['AWS', 'Azure', 'Terraform', 'Docker', 'Networking']),
                'industry': 'Tech'
            },
            {
                'role_id': str(uuid.uuid4()),
                'role_name': 'DevOps Engineer',
                'job_description': 'Automate CI/CD, infrastructure and monitoring pipelines.',
                'required_skills': json.dumps(['Docker', 'Kubernetes', 'Jenkins', 'Ansible', 'Python']),
                'industry': 'Tech'
            },
            {
                'role_id': str(uuid.uuid4()),
                'role_name': 'UI/UX Designer',
                'job_description': 'Create user-centred interfaces, wireframes and prototypes.',
                'required_skills': json.dumps(['Figma', 'User Research', 'Prototyping', 'HTML', 'CSS']),
                'industry': 'Design'
            },
            {
                'role_id': str(uuid.uuid4()),
                'role_name': 'Backend Developer',
                'job_description': 'Build server-side logic, APIs and data layers.',
                'required_skills': json.dumps(['Python', 'Node.js', 'REST', 'SQL', 'Git']),
                'industry': 'Tech'
            },
            {
                'role_id': str(uuid.uuid4()),
                'role_name': 'Frontend Developer',
                'job_description': 'Implement responsive user interfaces and client-side logic.',
                'required_skills': json.dumps(['JavaScript', 'React', 'CSS', 'HTML', 'Webpack']),
                'industry': 'Tech'
            },
            {
                'role_id': str(uuid.uuid4()),
                'role_name': 'Full-Stack Developer',
                'job_description': 'Work on both front-end and back-end codebases.',
                'required_skills': json.dumps(['JavaScript', 'React', 'Node.js', 'SQL', 'Git']),
                'industry': 'Tech'
            },
            {
                'role_id': str(uuid.uuid4()),
                'role_name': 'Business Analyst',
                'job_description': 'Bridge business needs and technical solutions via data and process analysis.',
                'required_skills': json.dumps(['Excel', 'SQL', 'Documentation', 'Agile', 'Communication']),
                'industry': 'Business'
            },
            {
                'role_id': str(uuid.uuid4()),
                'role_name': 'Project Manager',
                'job_description': 'Plan, execute and deliver projects on time and within budget.',
                'required_skills': json.dumps(['Agile', 'Scrum', 'Communication', 'Risk Management', 'Leadership']),
                'industry': 'Management'
            },
            {
                'role_id': str(uuid.uuid4()),
                'role_name': 'System Administrator',
                'job_description': 'Maintain servers, OS, backups and user accounts.',
                'required_skills': json.dumps(['Linux', 'Bash', 'Networking', 'AWS', 'Scripting']),
                'industry': 'Tech'
            },
            {
                'role_id': str(uuid.uuid4()),
                'role_name': 'QA Tester',
                'job_description': 'Design and execute test plans, automate regression suites.',
                'required_skills': json.dumps(['Selenium', 'Manual Testing', 'Python', 'JUnit', 'CI/CD']),
                'industry': 'Tech'
            },
            {
                'role_id': str(uuid.uuid4()),
                'role_name': 'Network Engineer',
                'job_description': 'Design, implement and troubleshoot network infrastructure.',
                'required_skills': json.dumps(['Cisco', 'Routing', 'Switching', 'TCP/IP', 'Firewalls']),
                'industry': 'Tech'
            },
            {
                'role_id': str(uuid.uuid4()),
                'role_name': 'Cybersecurity Analyst',
                'job_description': 'Monitor threats, perform vulnerability assessments, implement security controls.',
                'required_skills': json.dumps(['SIEM', 'Penetration Testing', 'Risk Assessment', 'Python', 'Network Security']),
                'industry': 'Security'
            },
            {
                'role_id': str(uuid.uuid4()),
                'role_name': 'Database Administrator',
                'job_description': 'Install, configure, secure and optimise database systems.',
                'required_skills': json.dumps(['SQL', 'PostgreSQL', 'Backup & Recovery', 'Performance Tuning', 'Linux']),
                'industry': 'Tech'
            }
        ]

        for role in default_roles:
            query('''
                INSERT INTO job_roles (role_id, role_name, job_description, required_skills, industry)
                VALUES (?, ?, ?, ?, ?)
            ''', [role['role_id'], role['role_name'], role['job_description'],
                  role['required_skills'], role['industry']])
        print("Default job roles seeded.")
