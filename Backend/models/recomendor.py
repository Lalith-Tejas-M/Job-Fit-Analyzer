import json
import requests
import yt_dlp
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError, as_completed

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL    = "llama3"

# Shared thread pool for YouTube fetches (avoids creating threads per-request)
_yt_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="yt_search")


# ------------------------------------------------------------------
# YouTube: fetch top N real videos (parallel, with per-skill timeout)
# ------------------------------------------------------------------
def _fetch_top_youtube_videos(skill: str, limit: int = 2) -> list:
    """
    Search YouTube for the best tutorial videos for a skill.
    Uses yt-dlp (no API key needed).
    Returns list of dicts: {title, url, views, channel, duration}
    Sorted by view count — most-watched videos first.
    """
    query = f"{skill} full course tutorial for beginners"
    ydl_opts = {
        "quiet":         True,
        "no_warnings":   True,
        "extract_flat":  True,
        "skip_download": True,
        "noplaylist":    True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info    = ydl.extract_info(f"ytsearch10:{query}", download=False)
            entries = info.get("entries", [])
            videos  = []
            for entry in entries:
                if not entry:
                    continue
                view_count = entry.get("view_count") or 0
                videos.append({
                    "title":           entry.get("title", ""),
                    "url":             f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                    "views":           view_count,
                    "views_formatted": f"{view_count:,}" if view_count else "N/A",
                    "channel":         entry.get("channel") or entry.get("uploader", ""),
                    "duration":        entry.get("duration_string") or str(entry.get("duration", "")),
                })
            videos.sort(key=lambda x: x["views"], reverse=True)
            return videos[:limit]
    except Exception as e:
        print(f"[YouTube Search] Failed for '{skill}': {e}")
        return []


def _fetch_videos_parallel(skills: list, limit: int = 2, timeout_per_skill: float = 12.0) -> dict:
    """
    Fetch YouTube videos for multiple skills in parallel.
    Each skill gets timeout_per_skill seconds. Returns {skill: [videos]} dict.
    """
    results = {s: [] for s in skills}
    futures = {_yt_executor.submit(_fetch_top_youtube_videos, s, limit): s for s in skills}
    for future in as_completed(futures, timeout=timeout_per_skill * len(skills)):
        skill = futures[future]
        try:
            results[skill] = future.result(timeout=timeout_per_skill)
        except Exception as e:
            print(f"[YouTube] Timeout/error for '{skill}': {e}")
    return results


# ------------------------------------------------------------------
# Ollama: generate personalized skill roadmap (with hard timeout)
# ------------------------------------------------------------------
def _call_ollama(
    missing_skills: list,
    match_score: float,
    resume=None,
    job_context=None,
    timeout: float = 35.0
) -> dict | None:
    """Call local Llama 3 via Ollama with a hard timeout."""
    try:
        skills_str    = ", ".join(missing_skills[:8]) if missing_skills else "None"
        resume_skills = str(resume.get("skills", ""))[:300] if resume and isinstance(resume, dict) else ""
        jd_snippet    = (job_context[:600] if job_context else "")

        prompt = f"""You are a senior career coach and technical mentor.

Candidate ATS Match Score: {round(match_score, 1)}%
Missing Skills: {skills_str}
Candidate Existing Skills: {resume_skills}
Job Context: {jd_snippet}

Generate a structured personalized career roadmap. Respond with ONLY a JSON object with exactly three keys:
- "short_term": array of 3 objects, each having: "skill" (string), "hours" (integer), "project" (string), "certificate" (string)
- "medium_term": array of 3 strings (goals for next 3-6 months)
- "long_term": array of 2 strings (career goals for 6-12 months)

Return ONLY valid JSON with no markdown, no explanation."""

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json"},
            timeout=timeout,
        )
        if response.status_code == 200:
            raw    = response.json().get("response", "{}")
            parsed = json.loads(raw)
            if all(k in parsed for k in ("short_term", "medium_term", "long_term")):
                return parsed
    except Exception as e:
        print(f"[Ollama] Recommendation failed: {e}")
    return None


def _build_fallback_plan(missing_skills: list, match_score: float) -> dict:
    """Fast offline fallback when Ollama is slow or unavailable."""
    short_term_raw = [
        {"skill": s, "hours": 10, "project": f"Build a hands-on project using {s}", "certificate": ""}
        for s in (missing_skills[:3] if missing_skills else ["Core Skills"])
    ]
    if match_score < 60:
        medium_term = [
            "Build 2-3 portfolio projects showcasing missing skills",
            "Contribute to an open-source project",
            "Earn one industry certification",
        ]
        long_term = [
            "Target mid-level roles after closing the skill gap",
            "Build a portfolio of 5+ significant projects",
        ]
    elif match_score < 80:
        medium_term = [
            "Deepen expertise in 2 core tech stacks",
            "Lead a small project end-to-end",
            "Pass one certificate exam",
        ]
        long_term = [
            "Aim for senior-level roles",
            "Write technical blogs or speak at meetups",
        ]
    else:
        medium_term = [
            "Prepare for system-design interviews",
            "Mentor junior developers",
            "Explore emerging technologies in your domain",
        ]
        long_term = [
            "Target staff / principal engineer level",
            "Develop deep domain expertise and thought leadership",
        ]
    return {"short_term": short_term_raw, "medium_term": medium_term, "long_term": long_term}


# ------------------------------------------------------------------
# Main entry point (fast path: Ollama + YouTube in parallel)
# ------------------------------------------------------------------
def generate_recommendations(
    missing_skills: list,
    match_score:    float,
    resume=None,
    job_context=None,
    ollama_timeout: float = 30.0,
) -> dict:
    """
    Generate a personalized learning roadmap.

    Performance optimizations:
    - Ollama runs with a 30-second hard timeout (was 45s blocking)
    - YouTube fetches for all skills run IN PARALLEL (was sequential)
    - Falls back instantly if Ollama is unavailable
    """

    # ── Step 1: Ollama plan (with timeout) ─────────────────────────
    # Run Ollama in a thread so we can apply a wall-clock timeout
    llm_plan = None
    with ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(_call_ollama, missing_skills, match_score, resume, job_context, ollama_timeout)
        try:
            llm_plan = future.result(timeout=ollama_timeout + 2)
        except Exception as e:
            print(f"[Recommender] Ollama timed out or failed ({e}). Using fallback.")

    if llm_plan:
        short_term_raw = llm_plan.get("short_term", [])
        medium_term    = llm_plan.get("medium_term", [])
        long_term      = llm_plan.get("long_term", [])
    else:
        fallback       = _build_fallback_plan(missing_skills, match_score)
        short_term_raw = fallback["short_term"]
        medium_term    = fallback["medium_term"]
        long_term      = fallback["long_term"]

    # Normalise short_term items
    items = []
    for item in short_term_raw:
        if isinstance(item, dict):
            skill = item.get("skill", "General")
        else:
            skill = str(item)
            item  = {"skill": skill, "hours": 10, "project": "", "certificate": ""}
        items.append((skill, item))

    # ── Step 2: Fetch YouTube videos for ALL skills in PARALLEL ────
    skills_to_fetch = [skill for skill, _ in items]
    print(f"[Recommender] Fetching YouTube videos for: {skills_to_fetch}")
    videos_map = _fetch_videos_parallel(skills_to_fetch, limit=2, timeout_per_skill=10.0)

    # ── Step 3: Assemble final short_term list ─────────────────────
    short_term = []
    for skill, item in items:
        short_term.append({
            "skill":       skill,
            "videos":      videos_map.get(skill, []),
            "hours":       item.get("hours", 10),
            "project":     item.get("project", f"Build a hands-on project using {skill}"),
            "certificate": item.get("certificate", ""),
        })

    return {
        "short_term":  short_term,
        "medium_term": medium_term,
        "long_term":   long_term,
    }