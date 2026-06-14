import json
import re
import requests

OLLAMA_BASE_URL = "http://localhost:11434"
PREFERRED_MODEL = "qwen2.5:7b-instruct"
FALLBACK_MODEL = "llama3"

# Compact, unambiguous prompt — shorter text = fewer tokens = faster response
_PROMPT_TEMPLATE = """\
Extract ALL information from this resume. Return ONLY valid JSON, no markdown, no explanation.

JSON Schema (follow this exactly):
{{"skills":[{{"skill":"Name","confidence":0.9}}],"education":[{{"degree":"BSc","branch":"CS","university":"MIT","year":"2022","confidence":0.9}}],"experience":[{{"company":"ABC Corp","role":"Software Engineer","date_range":"Jan 2022 - Present","confidence":0.9}}],"projects":[{{"project":"Title","tech_stack":["Python","Flask"],"summary":"Short description","confidence":0.9}}],"certifications":[{{"name":"AWS Solutions Architect","provider":"Amazon","year":"2023","confidence":0.9}}],"metadata":{{"skills_count":0,"projects_count":0,"experience_count":0,"certifications_count":0,"education_count":0,"overall_confidence":0.9}}}}

IMPORTANT RULES:
- Extract EVERY skill, library, tool, language, framework mentioned anywhere in the resume.
- Extract EVERY project listed under Projects or Academic Projects section.
- Extract EVERY certification, course, or award listed.
- If a field is unknown, use "Unknown" for strings and 0 for numbers.
- Return empty arrays [] if a section has no entries — do NOT omit keys.

Resume Text:
{text}
"""


def parse_resume_with_llm(text: str, timeout: int = 120) -> dict | None:
    """
    Calls local Ollama to extract structured resume information.
    Returns a fully-populated dict or None only if BOTH models fail.
    Timeout increased to 120s to prevent premature fallback.
    """
    # Truncate to 7000 chars — covers most single-page and two-page resumes
    prompt = _PROMPT_TEMPLATE.format(text=text[:7000])

    for model in [PREFERRED_MODEL, FALLBACK_MODEL]:
        try:
            print(f"[LLM Parser] Attempting extraction with {model}...")
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.1,   # Low temp = more deterministic, less hallucination
                        "num_predict": 1500,  # Enough for full JSON output
                    }
                },
                timeout=timeout
            )

            if response.status_code == 200:
                raw_json = response.json().get("response", "{}")
                parsed_data = _clean_and_parse_json(raw_json)

                if parsed_data and _is_valid_schema(parsed_data):
                    # Ensure all top-level keys exist so extractors never KeyError
                    _ensure_all_keys(parsed_data)
                    print(f"[LLM Parser] Successfully extracted data with {model}.")
                    return parsed_data
                else:
                    print(f"[LLM Parser] {model} returned invalid/incomplete JSON, trying next model.")
            else:
                print(f"[LLM Parser] Model {model} returned status code {response.status_code}")

        except requests.exceptions.Timeout:
            print(f"[LLM Parser] {model} timed out after {timeout}s, trying next model.")
            continue
        except requests.exceptions.RequestException as e:
            print(f"[LLM Parser] Request failed for model {model}: {e}")
            continue

    print("[LLM Parser] All models failed. Returning None — NO fallback caching.")
    return None


def _is_valid_schema(data: dict) -> bool:
    """Checks the LLM returned a proper dict with at least the skills key."""
    if not isinstance(data, dict):
        return False
    # Must have at least one of the main keys
    required = {"skills", "education", "experience", "projects", "certifications"}
    return bool(required & data.keys())


def _ensure_all_keys(data: dict):
    """Guarantees all expected top-level keys exist so extractors never crash with KeyError."""
    defaults = {
        "skills": [],
        "education": [],
        "experience": [],
        "projects": [],
        "certifications": [],
        "metadata": {}
    }
    for key, default in defaults.items():
        if key not in data:
            data[key] = default


def _clean_and_parse_json(raw: str) -> dict | None:
    """Attempt to parse JSON, with fallback regex repair for markdown code blocks."""
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences if model added them
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass

    # Extract content between outermost { and }
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None
