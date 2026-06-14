"""
migrate_reprocess_resumes.py
============================
Safely re-runs NLP extraction on all existing resumes that have
empty projects or experience fields and writes the results back
to the database.

Usage:
    cd "c:\\Users\\tejas\\OneDrive\\Desktop\\Machine Learning\\ML project"
    python migrate_reprocess_resumes.py

Requirements:
    - Flask server does NOT need to be running.
    - All Backend dependencies must be installed in the active Python env.
    - The Fluxbase database must be reachable.

IMPORTANT: Does NOT drop, rename, or change any table schema.
           Only UPDATEs the skills, education, experience, projects,
           certifications, experience_details, education_details columns
           on existing resume rows.
"""

import sys
import os
import json

# Allow importing Backend modules from this script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Backend'))

import database
from models.nlp_processor import (
    get_nlp_model,
    extract_skills,
    extract_education,
    extract_experience,
    extract_projects,
    extract_certifications,
)


def reprocess():
    print("=" * 55)
    print("  JOB FIT ANALYZER — Resume Reprocessing Migration")
    print("=" * 55)

    # 1. Load NLP models once
    print("\n[1/4] Loading NLP models...")
    nlp = get_nlp_model()
    print("      Models ready.")

    # 2. Fetch all resumes that need reprocessing
    #    We target rows where projects or experience_details are empty / '[]' / NULL
    print("\n[2/4] Fetching resumes to reprocess...")
    rows = database.query(
        """
        SELECT resume_id, parsed_text, projects, experience_details
        FROM resumes
        WHERE parsed_text IS NOT NULL AND parsed_text != ''
        """
    )

    if not rows:
        print("      No resumes found. Nothing to do.")
        return

    # Filter to only those with empty/missing projects or experience
    def _is_empty(val):
        if not val:
            return True
        try:
            return len(json.loads(val)) == 0
        except Exception:
            return True

    to_reprocess = [
        r for r in rows
        if _is_empty(r.get('projects')) or _is_empty(r.get('experience_details'))
    ]

    total = len(to_reprocess)
    print(f"      Found {total} resume(s) needing reprocessing (out of {len(rows)} total).")

    if total == 0:
        print("      All resumes already have data. Nothing to do.")
        return

    # 3. Reprocess each resume
    print("\n[3/4] Reprocessing resumes...\n")
    success = 0
    failed = 0

    for idx, row in enumerate(to_reprocess, start=1):
        resume_id = row['resume_id']
        text = row.get('parsed_text', '')

        print(f"  [{idx}/{total}] Resume ID: {resume_id}")

        if not text or len(text.strip()) < 50:
            print(f"          SKIP — parsed_text too short or empty.")
            failed += 1
            continue

        try:
            skills        = extract_skills(text, nlp)
            education     = extract_education(text, nlp)
            experience    = extract_experience(text, nlp)
            projects      = extract_projects(text)
            certifications = extract_certifications(text)

            print(f"          skills={len(skills)}  exp={len(experience)}  "
                  f"proj={len(projects)}  certs={len(certifications)}")

            # Update only the NLP-extracted columns — do not touch embedding or file fields
            database.query(
                """
                UPDATE resumes
                SET skills             = ?,
                    education          = ?,
                    experience         = ?,
                    experience_details = ?,
                    education_details  = ?,
                    projects           = ?,
                    certifications     = ?
                WHERE resume_id = ?
                """,
                [
                    json.dumps(skills),
                    json.dumps(education),
                    json.dumps(experience),
                    json.dumps(experience),   # experience_details mirrors experience
                    json.dumps(education),    # education_details mirrors education
                    json.dumps(projects),
                    json.dumps(certifications),
                    resume_id,
                ]
            )
            success += 1

        except Exception as e:
            print(f"          ERROR — {e}")
            failed += 1

    # 4. Summary
    print("\n" + "=" * 55)
    print(f"[4/4] Done.  Success: {success}   Failed/Skipped: {failed}")
    print("=" * 55)


if __name__ == '__main__':
    reprocess()
