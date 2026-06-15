import json
import re
import requests

OLLAMA_BASE_URL = "http://localhost:11434"

# FIX 2: Auto-detect best available model at startup instead of hardcoding
_detected_model = None   # primary (qwen or similar)
_fallback_model = None   # secondary (llama3 or similar)


def _detect_models() -> tuple[str, str]:
    """
    FIX 2: Query Ollama for locally installed models and pick the best pair.
    - Primary:  any qwen variant (fast, instruction-tuned)
    - Secondary: any llama3 / mistral / phi3 variant
    Called once at first use; result cached in module-level variables.
    """
    global _detected_model, _fallback_model

    if _detected_model is not None:
        return _detected_model, _fallback_model

    primary = None
    secondary = None

    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            models_data = resp.json().get("models", [])
            names = [m.get("name", "") for m in models_data]
            print(f"[LLM Parser] Available Ollama models: {names}")

            # Priority order for primary model (prefer qwen variants)
            primary_prefs = ["qwen", "gemma", "mistral", "phi"]
            # Priority order for fallback
            fallback_prefs = ["llama3", "llama2", "llama", "mistral", "phi"]

            for pref in primary_prefs:
                match = next((n for n in names if pref in n.lower()), None)
                if match:
                    primary = match
                    break

            for pref in fallback_prefs:
                match = next((n for n in names if pref in n.lower() and n != primary), None)
                if match:
                    secondary = match
                    break

            # If no preferred primary, just use the first two available
            if not primary and names:
                primary = names[0]
            if not secondary and len(names) > 1:
                secondary = names[1]

    except Exception as e:
        print(f"[LLM Parser] Could not auto-detect models: {e}")

    # Hard fallbacks if Ollama is unreachable
    if not primary:
        primary = "llama3"
    if not secondary:
        secondary = "llama3"

    _detected_model = primary
    _fallback_model = secondary

    print(f"[LLM Parser] Selected primary={primary}, fallback={secondary}")
    return _detected_model, _fallback_model


# Compact, unambiguous prompt — shorter text = fewer tokens = faster response
_PROMPT_TEMPLATE = """\
Extract ALL information from this resume. Return ONLY valid JSON, no markdown, no explanation.

JSON Schema (follow this exactly):
{{"skills":[{{"skill":"Name","confidence":0.9}}],"education":[{{"degree":"BSc","branch":"CS","university":"MIT","year":"2022","confidence":0.9}}],"experience":[{{"company":"ABC Corp","role":"Software Engineer","date_range":"Jan 2022 - Present","confidence":0.9}}],"projects":[{{"project":"Title","tech_stack":["Python","Flask"],"summary":"Short description","confidence":0.9}}],"certifications":[{{"name":"AWS Solutions Architect","provider":"Amazon","year":"2023","confidence":0.9}}],"metadata":{{"skills_count":0,"projects_count":0,"experience_count":0,"certifications_count":0,"education_count":0,"overall_confidence":0.9}}}}

IMPORTANT RULES:
- For skills: ONLY extract tool names, programming languages, frameworks, and libraries. Do NOT include project titles, sentences, or descriptions.
- Extract EVERY project listed under Projects or Academic Projects section.
- For each project, list its tech_stack as short tool/language names only (e.g. ["Python","TensorFlow","Flask"]).
- Extract EVERY certification, course, or award listed.
- If a field is unknown, use "Unknown" for strings and 0 for numbers.
- Return empty arrays [] if a section has no entries — do NOT omit keys.

Resume Text:
{text}
"""


def parse_resume_with_llm(text: str, timeout: int = 120) -> dict | None:
    """
    Calls local Ollama to extract structured resume information.
    FIX 2: Auto-detects the correct model names instead of hardcoding.
    Returns a fully-populated dict or None only if ALL models fail.
    """
    prompt = _PROMPT_TEMPLATE.format(text=text[:7000])

    # FIX 2: Get auto-detected model names
    primary_model, fallback_model = _detect_models()

    # Deduplicate so we don't try the same model twice
    models_to_try = [primary_model]
    if fallback_model and fallback_model != primary_model:
        models_to_try.append(fallback_model)

    for model in models_to_try:
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
                        "temperature": 0.1,   # Low temp = more deterministic
                        "num_predict": 1500,  # Enough for full JSON output
                    }
                },
                timeout=timeout
            )

            if response.status_code == 200:
                raw_json = response.json().get("response", "{}")
                parsed_data = _clean_and_parse_json(raw_json)

                if parsed_data and _is_valid_schema(parsed_data):
                    _ensure_all_keys(parsed_data)
                    print(f"[LLM Parser] Successfully extracted data with {model}.")
                    return parsed_data
                else:
                    print(f"[LLM Parser] {model} returned invalid/incomplete JSON, trying next model.")
            elif response.status_code == 404:
                # Model not found — reset cache so next request re-detects
                print(f"[LLM Parser] Model '{model}' returned 404 (not found). Resetting model cache.")
                global _detected_model, _fallback_model
                _detected_model = None
                _fallback_model = None
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
