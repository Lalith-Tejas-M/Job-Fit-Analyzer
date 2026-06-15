import re

filepath = "Backend/models/recomendor.py"
with open(filepath, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update imports
old_imports = """import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed"""

new_imports = """import json
import requests
import re
import urllib.parse
import html
from concurrent.futures import ThreadPoolExecutor, as_completed"""

code = code.replace(old_imports, new_imports)

# 2. Extract and replace the massive _SKILL_RESOURCES + _generic_resources block
# Let's search from the start of _SKILL_RESOURCES to the end of _generic_resources
start_pat = "_SKILL_RESOURCES = {"
end_pat = '        "project": f"Build a hands-on project demonstrating {skill}"\n    }'

start_idx = code.find(start_pat)
end_idx = code.find(end_pat)

if start_idx != -1 and end_idx != -1:
    end_idx += len(end_pat)
    
    # Define our new dynamic web search helper functions
    dynamic_search_code = """def _search_ddg(query: str, limit: int = 1) -> list:
    \"\"\"Perform a live DuckDuckGo HTML search and extract top links.\"\"\"
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code != 200:
            return []
        matches = re.findall(r'class="result__a"\\s+href="([^"]+)"[^>]*>(.*?)</a>', r.text, re.DOTALL)
        results = []
        for href, title_html in matches:
            if 'uddg=' in href:
                uddg_match = re.search(r'uddg=([^&]+)', href)
                if uddg_match:
                    raw_url = urllib.parse.unquote(uddg_match.group(1))
                    if "duckduckgo.com" in raw_url:
                        continue
                    title = html.unescape(re.sub(r'<[^>]+>', '', title_html)).strip()
                    results.append({"title": title, "url": raw_url})
                    if len(results) >= limit:
                        break
        return results
    except Exception as e:
        print(f"[DDG Search] Failed query '{query}': {e}")
        return []


def _fetch_all_dynamic_resources_parallel(skills: list) -> dict:
    \"\"\"
    Search internet (DDG) for docs, courses, and practice links for all skills in parallel.
    Returns a dict mapping skill to a list of resources.
    \"\"\"
    results_map = {s: [] for s in skills}
    if not skills:
        return results_map
        
    jobs = []
    for s in skills:
        jobs.append((f"{s} official documentation", s, "docs", f"{s} Official Documentation"))
        jobs.append((f"{s} online course tutorial", s, "course", f"{s} Tutorial Course"))
        jobs.append((f"{s} practice hands-on exercises", s, "practice", f"{s} Practice Exercises"))
        
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {}
        for query, skill, r_type, fallback_title in jobs:
            f = executor.submit(_search_ddg, query, 1)
            futures[f] = (skill, r_type, fallback_title)
            
        for f in as_completed(futures):
            skill, r_type, fallback_title = futures[f]
            try:
                search_res = f.result()
                if search_res:
                    res_item = search_res[0]
                    results_map[skill].append({
                        "type": r_type,
                        "title": res_item["title"],
                        "url": res_item["url"]
                    })
                else:
                    q_encoded = urllib.parse.quote(f"{skill} {r_type}")
                    results_map[skill].append({
                        "type": r_type,
                        "title": fallback_title,
                        "url": f"https://www.google.com/search?q={q_encoded}"
                    })
            except Exception as e:
                print(f"[Resource Fetcher] Future error: {e}")
                q_encoded = urllib.parse.quote(f"{skill} {r_type}")
                results_map[skill].append({
                    "type": r_type,
                    "title": fallback_title,
                    "url": f"https://www.google.com/search?q={q_encoded}"
                })
                
    return results_map"""

    code = code[:start_idx] + dynamic_search_code + code[end_idx:]
    print("Replaced curated resources list with dynamic DDG search functions.")
else:
    print("Could not find start/end pattern for _SKILL_RESOURCES.")

# 3. Replace _build_fallback_plan
old_fallback = """def _build_fallback_plan(missing_skills: list, match_score: float) -> dict:
    \"\"\"FIX 3: Rich offline fallback using curated _SKILL_RESOURCES.\"\"\"
    short_term_raw = []
    for s in (missing_skills[:5] if missing_skills else ["Core Skills"]):
        res = _SKILL_RESOURCES.get(s, _generic_resources(s))
        short_term_raw.append({
            "skill": s,
            "hours": res["hours"],
            "steps": res["steps"],
            "project": res["project"],
            "certificate": res["certificate"]
        })"""

new_fallback = """def _build_fallback_plan(missing_skills: list, match_score: float) -> dict:
    \"\"\"Offline fallback plan using generic but clean templates (no hardcoded URLs).\"\"\"
    short_term_raw = []
    for s in (missing_skills[:5] if missing_skills else ["Core Skills"]):
        short_term_raw.append({
            "skill": s,
            "hours": 15,
            "steps": [
                f"1. Understand the core syntax and concepts of {s} (3h)",
                f"2. Read the official documentation and API guides for {s} (4h)",
                f"3. Complete a hands-on tutorial or mini-course (4h)",
                f"4. Build a practice project to apply {s} in a real scenario (4h)"
            ],
            "project": f"Build a portfolio project demonstrating {s} capabilities",
            "certificate": f"Certified {s} Professional / Developer"
        })"""

code = code.replace(old_fallback, new_fallback)

# 4. Replace generate_recommendations steps 2 & 3
# Let's find step 2 start and replace to the end
old_gen_rec_tail = """    # ── Step 2: Fetch YouTube videos for ALL skills in PARALLEL (FIX 4) ────
    skills_to_fetch = [skill for skill, _ in items]
    print(f"[Recommender] Fetching YouTube videos for: {skills_to_fetch}")
    videos_map = _fetch_videos_parallel(skills_to_fetch, limit=2, timeout_per_skill=5.0)

    # ── Step 3: Merge curated resources + Ollama steps + YouTube ──────────
    short_term = []
    for skill, item in items:
        # Pull curated resource list (docs, courses, practice sites)
        curated = _SKILL_RESOURCES.get(skill, _generic_resources(skill))

        # Use Ollama steps if available, else fall back to curated steps
        steps = item.get("steps") or curated["steps"]
        project = item.get("project") or curated["project"]
        certificate = item.get("certificate") or curated.get("certificate", "")
        hours = item.get("hours") or curated["hours"]

        # Add YouTube videos as an extra resource type
        yt_videos = videos_map.get(skill, [])
        resources = list(curated["resources"])  # copy curated resources
        for vid in yt_videos:
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
    }"""

new_gen_rec_tail = """    # ── Step 2: Fetch YouTube videos AND dynamic resources in parallel ────
    skills_to_fetch = [skill for skill, _ in items]
    print(f"[Recommender] Fetching YouTube videos for: {skills_to_fetch}")
    videos_map = _fetch_videos_parallel(skills_to_fetch, limit=2, timeout_per_skill=5.0)

    print(f"[Recommender] Dynamically researching search engines for: {skills_to_fetch}")
    dynamic_resources_map = _fetch_all_dynamic_resources_parallel(skills_to_fetch)

    # ── Step 3: Merge dynamic resources + Ollama steps + YouTube ──────────
    short_term = []
    for skill, item in items:
        # Get the dynamically fetched resources for this skill (docs, course, practice)
        resources = list(dynamic_resources_map.get(skill, []))

        # Use Ollama steps if available, else fall back to dynamic steps
        steps = item.get("steps")
        if not steps:
            steps = [
                f"1. Understand the core syntax and concepts of {skill} (3h)",
                f"2. Read the official documentation and API guides for {skill} (4h)",
                f"3. Complete a hands-on tutorial or mini-course (4h)",
                f"4. Build a practice project to apply {skill} in a real scenario (4h)"
            ]
        project = item.get("project") or f"Build a portfolio project demonstrating {skill} capabilities"
        certificate = item.get("certificate") or ""
        hours = item.get("hours") or 15

        # Add YouTube videos as an extra resource type
        yt_videos = videos_map.get(skill, [])
        for vid in yt_videos:
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
    }"""

# Since line endings on Windows might be CRLF, let's normalize everything to LF for match,
# then write it back
code_norm = code.replace("\r\n", "\n")
old_gen_rec_tail_norm = old_gen_rec_tail.replace("\r\n", "\n")
new_gen_rec_tail_norm = new_gen_rec_tail.replace("\r\n", "\n")

if old_gen_rec_tail_norm in code_norm:
    code_norm = code_norm.replace(old_gen_rec_tail_norm, new_gen_rec_tail_norm_)
    print("Replaced generate_recommendations tail successfully.")
else:
    # Let's try matching a smaller substring if full match failed due to minor difference
    print("Full tail match failed, searching by regex...")
    # Replace from step 2 comment to the end of the string
    pat = re.escape("    # ── Step 2: Fetch YouTube videos for ALL skills in PARALLEL (FIX 4) ────") + ".*"
    code_norm, count = re.subn(pat, new_gen_rec_tail_norm, code_norm, flags=re.DOTALL)
    print(f"Substituted tail: {count} matches.")

with open(filepath, "w", encoding="utf-8", newline="\n") as f:
    f.write(code_norm)
print("File written successfully.")
