import json
import re
import html
import urllib.parse
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

OLLAMA_BASE_URL = "http://localhost:11434"

# Shared thread pool (avoids creating threads per-request)
_yt_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="yt_search")


# ------------------------------------------------------------------
# YouTube: fetch top N real videos via yt-dlp (parallel, with timeout)
# ------------------------------------------------------------------
def _fetch_top_youtube_videos(skill: str, limit: int = 2) -> list:
    """
    Search YouTube for the best tutorial videos for a skill.
    Uses yt-dlp (no API key needed). Returns list of dicts.
    """
    try:
        import yt_dlp
        query = f"{skill} tutorial beginner"
        ydl_opts = {
            "quiet":         True,
            "no_warnings":   True,
            "extract_flat":  True,
            "skip_download": True,
            "noplaylist":    True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info    = ydl.extract_info(f"ytsearch3:{query}", download=False)
            entries = info.get("entries", [])
            videos  = []
            for entry in entries:
                if not entry:
                    continue
                view_count = entry.get("view_count") or 0
                videos.append({
                    "title":   entry.get("title", ""),
                    "url":     f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                    "views":   view_count,
                    "channel": entry.get("channel") or entry.get("uploader", ""),
                })
            videos.sort(key=lambda x: x["views"], reverse=True)
            return videos[:limit]
    except Exception as e:
        print(f"[YouTube Search] Failed for '{skill}': {e}")
        return []


def _fetch_videos_parallel(skills: list, limit: int = 2, timeout_per_skill: float = 5.0) -> dict:
    """Fetch YouTube videos for all skills in parallel with per-skill timeout."""
    results = {s: [] for s in skills}
    futures = {_yt_executor.submit(_fetch_top_youtube_videos, s, limit): s for s in skills}
    for future in as_completed(futures, timeout=timeout_per_skill * max(len(skills), 1)):
        skill = futures[future]
        try:
            results[skill] = future.result(timeout=timeout_per_skill)
        except Exception as e:
            print(f"[YouTube] Timeout/error for '{skill}': {e}")
    return results


# ------------------------------------------------------------------
# Live DuckDuckGo web search — no API key, no hardcoded URLs
# ------------------------------------------------------------------
def _search_ddg(query: str, limit: int = 1) -> list:
    """
    Perform a real-time DuckDuckGo HTML search and return top links.
    Returns list of {title, url} dicts.
    """
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        r = requests.get(url, headers=headers, timeout=6)
        if r.status_code != 200:
            return []

        matches = re.findall(
            r'class="result__a"\s+href="([^"]+)"[^>]*>(.*?)</a>',
            r.text,
            re.DOTALL,
        )
        results = []
        for href, title_raw in matches:
            if "uddg=" not in href:
                continue
            m = re.search(r"uddg=([^&]+)", href)
            if not m:
                continue
            raw_url = urllib.parse.unquote(m.group(1))
            # Skip DDG internal pages
            if "duckduckgo.com" in raw_url:
                continue
            title = html.unescape(re.sub(r"<[^>]+>", "", title_raw)).strip()
            if not title or not raw_url:
                continue
            results.append({"title": title, "url": raw_url})
            if len(results) >= limit:
                break
        return results
    except Exception as e:
        print(f"[DDG Search] Failed for query '{query}': {e}")
        return []


def _fetch_all_resources_for_skills(skills: list) -> dict:
    """
    Searches DuckDuckGo in PARALLEL for docs, courses, and practice sites
    for every skill. Returns {skill: [resource_dicts]}.

    Each search query is tuned to surface the BEST real page:
      - docs:     "{skill} official documentation site"
      - course:   "{skill} free online course tutorial"
      - practice: "{skill} hands-on exercises practice site"
    """
    resources_map = {s: [] for s in skills}
    if not skills:
        return resources_map

    # Build all search jobs
    jobs = []
    for s in skills:
        jobs.append((f"{s} official documentation", s, "docs"))
        jobs.append((f"{s} free online course tutorial", s, "course"))
        jobs.append((f"{s} hands-on exercises practice problems", s, "practice"))

    print(f"[Recommender] Launching {len(jobs)} DDG resource searches in parallel...")

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {}
        for query, skill, r_type in jobs:
            f = executor.submit(_search_ddg, query, 1)
            futures[f] = (skill, r_type, query)

        for f in as_completed(futures, timeout=15):
            skill, r_type, query = futures[f]
            try:
                search_res = f.result()
                if search_res:
                    item = search_res[0]
                    resources_map[skill].append({
                        "type":  r_type,
                        "title": item["title"],
                        "url":   item["url"],
                    })
                else:
                    # Graceful fallback: link to a Google search so user still gets something
                    q_enc = urllib.parse.quote(query)
                    resources_map[skill].append({
                        "type":  r_type,
                        "title": f"{skill} — {r_type.capitalize()} Resources",
                        "url":   f"https://www.google.com/search?q={q_enc}",
                    })
            except Exception as e:
                print(f"[Resource Fetcher] Error for '{skill}' ({r_type}): {e}")
                q_enc = urllib.parse.quote(query)
                resources_map[skill].append({
                    "type":  r_type,
                    "title": f"{skill} — {r_type.capitalize()} Resources",
                    "url":   f"https://www.google.com/search?q={q_enc}",
                })

    return resources_map


# ------------------------------------------------------------------
# Ollama: generate personalized skill roadmap (with hard timeout)
# ------------------------------------------------------------------
def _call_ollama(
    missing_skills: list,
    match_score: float,
    resume=None,
    job_context=None,
    timeout: float = 35.0,
) -> dict | None:
    """Call local Ollama to generate a rich, structured career roadmap."""
    try:
        from models.llm_resume_parser import _detect_models
        _, model = _detect_models()
    except Exception:
        model = "llama3"

    try:
        skills_str    = ", ".join(missing_skills[:8]) if missing_skills else "None"
        resume_skills = str(resume.get("skills", ""))[:300] if resume and isinstance(resume, dict) else ""
        jd_snippet    = (job_context[:500] if job_context else "")

        prompt = f"""You are a senior career coach and technical mentor.

Candidate ATS Match Score: {round(match_score, 1)}%
Missing Skills: {skills_str}
Candidate Existing Skills: {resume_skills}
Job Context: {jd_snippet}

Generate a structured personalized career roadmap. Respond with ONLY a JSON object:
{{
  "short_term": [
    {{
      "skill": "SkillName",
      "hours": 15,
      "steps": [
        "1. Learn the fundamentals of SkillName (Xh)",
        "2. Complete a hands-on tutorial (Xh)",
        "3. Build a small project (Xh)",
        "4. Integrate into a portfolio project (Xh)"
      ],
      "project": "Brief project idea using this skill",
      "certificate": "Relevant certification name or empty string"
    }}
  ],
  "medium_term": ["goal 1", "goal 2", "goal 3"],
  "long_term": ["career goal 1", "career goal 2"]
}}

Return ONLY valid JSON. One entry in short_term per missing skill (max 5 skills)."""

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "format": "json",
                  "options": {"temperature": 0.2, "num_predict": 1200}},
            timeout=timeout,
        )
        if response.status_code == 200:
            raw    = response.json().get("response", "{}")
            parsed = json.loads(raw)
            if all(k in parsed for k in ("short_term", "medium_term", "long_term")):
                return parsed
    except Exception as e:
        print(f"[Ollama Recommender] Recommendation failed: {e}")
    return None


def _build_fallback_plan(missing_skills: list, match_score: float) -> dict:
    """Offline fallback — uses clean generic steps (no hardcoded external URLs)."""
    short_term_raw = []
    for s in (missing_skills[:5] if missing_skills else ["Core Skills"]):
        short_term_raw.append({
            "skill": s,
            "hours": 15,
            "steps": [
                f"1. Understand the core syntax and concepts of {s} (3h)",
                f"2. Read the official documentation and follow quick-start guides (4h)",
                f"3. Complete a hands-on tutorial or mini-course (4h)",
                f"4. Build a practice project that applies {s} end-to-end (4h)",
            ],
            "project": f"Build a portfolio project demonstrating {s} capabilities",
            "certificate": f"Search for a certified {s} course on Coursera or Udemy",
        })

    if match_score < 60:
        medium_term = [
            "Build 2-3 portfolio projects showcasing your missing skills",
            "Contribute to an open-source project on GitHub",
            "Earn one industry certification in your strongest missing skill",
        ]
        long_term = [
            "Target mid-level roles after closing the current skill gap",
            "Build a portfolio of 5+ significant projects with live demos",
        ]
    elif match_score < 80:
        medium_term = [
            "Deepen expertise in 2 core tech stacks required for this role",
            "Lead a small personal or freelance project end-to-end",
            "Pass one certificate exam relevant to the job description",
        ]
        long_term = [
            "Aim for senior-level roles once portfolio is strong",
            "Write technical blogs or speak at local tech meetups",
        ]
    else:
        medium_term = [
            "Prepare for system-design interviews",
            "Mentor junior developers in your team or community",
            "Explore emerging technologies in your domain (e.g., LLMs, MLOps)",
        ]
        long_term = [
            "Target staff / principal engineer level positions",
            "Develop deep domain expertise and thought leadership",
        ]
    return {"short_term": short_term_raw, "medium_term": medium_term, "long_term": long_term}


# ------------------------------------------------------------------
# Main entry point — fully dynamic, no hardcoded resource URLs
# ------------------------------------------------------------------
def generate_recommendations(
    missing_skills: list,
    match_score:    float,
    resume=None,
    job_context=None,
    ollama_timeout: float = 30.0,
) -> dict:
    """
    Generate a personalized learning roadmap with live, internet-fetched resources.

    Pipeline:
      1. Ask Ollama to produce skill steps / project ideas / certificate names.
      2. Fetch REAL YouTube tutorials via yt-dlp (parallel, 5s timeout per skill).
      3. Fetch REAL docs / course / practice URLs via live DuckDuckGo search (parallel).
      4. Merge everything per skill card — zero hardcoded URLs.
    """
    # ── Step 1: Ollama LLM plan ─────────────────────────────────────
    llm_plan = None
    with ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(_call_ollama, missing_skills, match_score, resume, job_context, ollama_timeout)
        try:
            llm_plan = future.result(timeout=ollama_timeout + 2)
        except Exception as e:
            print(f"[Recommender] Ollama timed out or failed ({e}). Using fallback plan.")

    if llm_plan:
        short_term_raw = llm_plan.get("short_term", [])
        medium_term    = llm_plan.get("medium_term", [])
        long_term      = llm_plan.get("long_term", [])
    else:
        fallback       = _build_fallback_plan(missing_skills, match_score)
        short_term_raw = fallback["short_term"]
        medium_term    = fallback["medium_term"]
        long_term      = fallback["long_term"]

    # Normalise short_term items into (skill, item) tuples
    items = []
    for item in short_term_raw[:5]:
        if isinstance(item, dict):
            skill = item.get("skill", "General")
        else:
            skill = str(item)
            item  = {"skill": skill, "hours": 15, "steps": [], "project": "", "certificate": ""}
        items.append((skill, item))

    skills_to_fetch = [skill for skill, _ in items]

    # ── Step 2: YouTube + DDG fetch run IN PARALLEL ─────────────────
    # Launch both at the same time so they overlap.
    with ThreadPoolExecutor(max_workers=2) as pool:
        yt_future  = pool.submit(_fetch_videos_parallel, skills_to_fetch, 2, 5.0)
        ddg_future = pool.submit(_fetch_all_resources_for_skills, skills_to_fetch)

        videos_map          = yt_future.result()
        dynamic_resources   = ddg_future.result()

    # ── Step 3: Merge everything into final short_term cards ─────────
    short_term = []
    for skill, item in items:
        # Steps: prefer Ollama-generated, else generate generic
        steps = item.get("steps")
        if not steps:
            steps = [
                f"1. Understand the core syntax and concepts of {skill} (3h)",
                f"2. Read the official documentation and follow quick-start guides (4h)",
                f"3. Complete a hands-on tutorial or mini-course (4h)",
                f"4. Build a practice project that applies {skill} end-to-end (4h)",
            ]

        project     = item.get("project") or f"Build a portfolio project demonstrating {skill} capabilities"
        certificate = item.get("certificate") or ""
        hours       = item.get("hours") or 15

        # Resources: all from LIVE DDG search (docs, course, practice)
        resources = list(dynamic_resources.get(skill, []))

        # Append YouTube video links as 'video' type resources
        for vid in videos_map.get(skill, []):
            resources.append({
                "type":  "video",
                "title": vid.get("title", f"{skill} Tutorial"),
                "url":   vid.get("url", ""),
            })

        short_term.append({
            "skill":       skill,
            "hours":       hours,
            "steps":       steps,
            "project":     project,
            "certificate": certificate,
            "resources":   resources,
        })

    return {
        "short_term":  short_term,
        "medium_term": medium_term,
        "long_term":   long_term,
    }