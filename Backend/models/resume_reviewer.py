import json
import requests

def review_resume(resume_text: str, job_description: str) -> dict:
    """Review resume against job description using Ollama Llama 3"""
    try:
        prompt = f"""
        You are an expert ATS Resume Reviewer.
        
        Resume (truncated): {resume_text[:2000]}...
        Job Description (truncated): {job_description[:1000]}...
        
        Provide a detailed review in STRICT JSON format with exactly four keys:
        "missing_keywords": array of strings (keywords from JD missing in resume)
        "weak_sections": array of strings (which sections of the resume need improvement and why)
        "ats_suggestions": array of strings (formatting or content suggestions for better ATS parsing)
        "improved_bullets": array of strings (3 examples of rewriting their bullet points to be more impactful)
        
        Return ONLY valid JSON. Do not include markdown formatting or conversational text.
        """
        response = requests.post('http://localhost:11434/api/generate', json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return json.loads(result['response'])
    except Exception as e:
        print(f"Ollama resume review failed: {e}")
        
    return {
        "missing_keywords": ["Could not generate insights (Local LLM is offline or busy)"],
        "weak_sections": [],
        "ats_suggestions": [],
        "improved_bullets": []
    }
