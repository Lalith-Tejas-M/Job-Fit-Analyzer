import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

OLLAMA_BASE_URL = "http://localhost:11434"

# FIX 4: Shared thread pool (avoids creating threads per-request)
_yt_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="yt_search")


# ------------------------------------------------------------------
# YouTube: fetch top N real videos (parallel, with per-skill timeout)
# FIX 4: Reduced search to 3 results (was 10) for speed
# ------------------------------------------------------------------
def _fetch_top_youtube_videos(skill: str, limit: int = 2) -> list:
    """
    Search YouTube for the best tutorial videos for a skill.
    Uses yt-dlp (no API key needed).
    Returns list of dicts: {title, url, views, channel, duration}
    FIX 4: Only fetches top 3 results instead of 10 for speed.
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
            info    = ydl.extract_info(f"ytsearch3:{query}", download=False)  # was ytsearch10
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
    """
    FIX 4: Timeout reduced from 12s → 5s per skill. Fetch in parallel.
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
# Static resource library — curated learning resources per skill
# FIX 3: Rich per-skill preparation paths
# ------------------------------------------------------------------
_SKILL_RESOURCES = {
    "Python": {
        "steps": [
            "1. Master Python basics: variables, loops, functions, OOP (3h)",
            "2. Learn file I/O, error handling, and modules (2h)",
            "3. Practice with 5 small scripts (data processing, automation) (5h)",
            "4. Build a real project (API or automation tool) (5h)"
        ],
        "resources": [
            {"type": "docs",     "title": "Python Official Tutorial",        "url": "https://docs.python.org/3/tutorial/"},
            {"type": "course",   "title": "freeCodeCamp Python Full Course", "url": "https://www.youtube.com/watch?v=rfscVS0vtbw"},
            {"type": "practice", "title": "HackerRank Python Track",         "url": "https://www.hackerrank.com/domains/python"},
        ],
        "hours": 15, "certificate": "PCAP – Certified Associate in Python Programming",
        "project": "Build a resume parser or data pipeline script"
    },
    "Machine Learning": {
        "steps": [
            "1. Understand ML fundamentals: regression, classification, clustering (4h)",
            "2. Learn scikit-learn: train/test split, pipelines, metrics (4h)",
            "3. Study gradient boosting and neural networks (4h)",
            "4. Build an end-to-end ML project with a real dataset (8h)"
        ],
        "resources": [
            {"type": "docs",     "title": "Scikit-learn User Guide",              "url": "https://scikit-learn.org/stable/user_guide.html"},
            {"type": "course",   "title": "Andrew Ng ML Specialization (Coursera)","url": "https://www.coursera.org/specializations/machine-learning-introduction"},
            {"type": "practice", "title": "Kaggle Learn ML",                      "url": "https://www.kaggle.com/learn/intro-to-machine-learning"},
        ],
        "hours": 25, "certificate": "TensorFlow Developer Certificate",
        "project": "End-to-end churn prediction API with Flask"
    },
    "Deep Learning": {
        "steps": [
            "1. Understand neural network architecture: layers, activations, backprop (4h)",
            "2. Learn PyTorch or TensorFlow basics (4h)",
            "3. Implement CNNs for image classification (4h)",
            "4. Experiment with RNNs/Transformers on text data (4h)"
        ],
        "resources": [
            {"type": "docs",     "title": "PyTorch Tutorials",               "url": "https://pytorch.org/tutorials/"},
            {"type": "course",   "title": "fast.ai Practical Deep Learning", "url": "https://course.fast.ai"},
            {"type": "practice", "title": "Kaggle Competitions",             "url": "https://www.kaggle.com/competitions"},
        ],
        "hours": 30, "certificate": "TensorFlow Developer Certificate",
        "project": "Image classifier with REST API deployment"
    },
    "TensorFlow": {
        "steps": [
            "1. Learn tensors, operations, and tf.data pipeline (3h)",
            "2. Build and train a neural network from scratch (4h)",
            "3. Use Keras high-level API for CNNs and RNNs (4h)",
            "4. Deploy a TF model with TF Serving or Flask (4h)"
        ],
        "resources": [
            {"type": "docs",     "title": "TensorFlow Official Tutorials", "url": "https://www.tensorflow.org/tutorials"},
            {"type": "course",   "title": "DeepLearning.AI TF Developer", "url": "https://www.coursera.org/professional-certificates/tensorflow-in-practice"},
            {"type": "practice", "title": "TF Playground",                "url": "https://playground.tensorflow.org"},
        ],
        "hours": 20, "certificate": "TensorFlow Developer Certificate",
        "project": "Train and deploy an image classifier"
    },
    "PyTorch": {
        "steps": [
            "1. Understand tensors and autograd (2h)",
            "2. Build a simple linear model and train loop (3h)",
            "3. Implement CNNs with PyTorch nn.Module (4h)",
            "4. Use DataLoader and train on a Kaggle dataset (4h)"
        ],
        "resources": [
            {"type": "docs",     "title": "PyTorch Official Docs",      "url": "https://pytorch.org/tutorials/"},
            {"type": "course",   "title": "fast.ai Deep Learning Part 1","url": "https://course.fast.ai"},
            {"type": "practice", "title": "Kaggle Intro to DL",         "url": "https://www.kaggle.com/learn/intro-to-deep-learning"},
        ],
        "hours": 20, "certificate": "PyTorch Fundamentals (Microsoft Learn)",
        "project": "Custom image classifier with transfer learning"
    },
    "NLP": {
        "steps": [
            "1. Learn text preprocessing: tokenization, stemming, TF-IDF (3h)",
            "2. Study Word2Vec, GloVe, and sentence embeddings (3h)",
            "3. Fine-tune a BERT model on a classification task (4h)",
            "4. Build an NLP pipeline (sentiment analysis / NER) (4h)"
        ],
        "resources": [
            {"type": "docs",     "title": "HuggingFace NLP Course",    "url": "https://huggingface.co/learn/nlp-course"},
            {"type": "course",   "title": "Stanford NLP (YouTube)",    "url": "https://www.youtube.com/playlist?list=PLoROMvodv4rMFqRtEuo6SGjY4XbRIVx76"},
            {"type": "practice", "title": "Kaggle NLP Competitions",   "url": "https://www.kaggle.com/competitions?search=nlp"},
        ],
        "hours": 20, "certificate": "HuggingFace NLP Course Certificate",
        "project": "Text classification or resume parser with BERT"
    },
    "Docker": {
        "steps": [
            "1. Learn Docker fundamentals: images, containers, Dockerfile (2h)",
            "2. Run and expose a Flask API in a container (2h)",
            "3. Use docker-compose for multi-container apps (2h)",
            "4. Push an image to Docker Hub / container registry (1h)"
        ],
        "resources": [
            {"type": "docs",     "title": "Docker Official Get Started",       "url": "https://docs.docker.com/get-started/"},
            {"type": "course",   "title": "TechWorld Docker Full Course",      "url": "https://www.youtube.com/watch?v=zJ6WbK9zFpI"},
            {"type": "practice", "title": "Play with Docker (browser labs)",   "url": "https://labs.play-with-docker.com"},
        ],
        "hours": 8, "certificate": "Docker Certified Associate",
        "project": "Containerize a multi-service Node.js + Postgres app"
    },
    "Kubernetes": {
        "steps": [
            "1. Understand Pods, Deployments, Services, and Ingress (3h)",
            "2. Set up minikube locally and deploy a sample app (3h)",
            "3. Configure auto-scaling and rolling updates (2h)",
            "4. Deploy with Helm charts and namespaces (2h)"
        ],
        "resources": [
            {"type": "docs",     "title": "Kubernetes Official Docs",        "url": "https://kubernetes.io/docs/home/"},
            {"type": "course",   "title": "TechWorld K8s Full Course",       "url": "https://www.youtube.com/watch?v=X48VuDVv0do"},
            {"type": "practice", "title": "Killercoda Kubernetes Scenarios", "url": "https://killercoda.com/kubernetes"},
        ],
        "hours": 12, "certificate": "CKAD – Certified Kubernetes App Developer",
        "project": "Deploy a microservices app on minikube with auto-scaling"
    },
    "AWS": {
        "steps": [
            "1. Understand core services: EC2, S3, IAM, VPC (3h)",
            "2. Deploy a static site on S3 + CloudFront (2h)",
            "3. Set up a CI/CD pipeline with CodePipeline (3h)",
            "4. Deploy a backend API on Lambda or EC2 (4h)"
        ],
        "resources": [
            {"type": "docs",     "title": "AWS Getting Started",            "url": "https://aws.amazon.com/getting-started/"},
            {"type": "course",   "title": "freeCodeCamp AWS Full Course",   "url": "https://www.youtube.com/watch?v=3hLmDS179YE"},
            {"type": "practice", "title": "AWS Skill Builder (Free Labs)",  "url": "https://skillbuilder.aws"},
        ],
        "hours": 20, "certificate": "AWS Cloud Practitioner",
        "project": "Host a full-stack app with CI/CD on AWS"
    },
    "SQL": {
        "steps": [
            "1. Learn SELECT, WHERE, JOINs, GROUP BY fundamentals (2h)",
            "2. Practice subqueries, window functions, CTEs (2h)",
            "3. Design a normalized database schema (2h)",
            "4. Optimize slow queries with indexes and EXPLAIN (2h)"
        ],
        "resources": [
            {"type": "docs",     "title": "PostgreSQL Official Tutorial",    "url": "https://www.postgresql.org/docs/current/tutorial.html"},
            {"type": "course",   "title": "Mode SQL Tutorial",               "url": "https://mode.com/sql-tutorial/"},
            {"type": "practice", "title": "SQLZoo Interactive Exercises",    "url": "https://sqlzoo.net"},
        ],
        "hours": 8, "certificate": "Oracle SQL Certified Associate",
        "project": "Design and query a Netflix-style database"
    },
    "React": {
        "steps": [
            "1. Learn JSX, props, state, and component lifecycle (3h)",
            "2. Use hooks: useState, useEffect, useContext (3h)",
            "3. Manage state with React Query or Redux Toolkit (3h)",
            "4. Build a full app with routing and API integration (4h)"
        ],
        "resources": [
            {"type": "docs",     "title": "React Official Docs (react.dev)", "url": "https://react.dev/learn"},
            {"type": "course",   "title": "The Odin Project React Path",     "url": "https://www.theodinproject.com/paths/full-stack-javascript/courses/react"},
            {"type": "practice", "title": "Frontend Mentor Challenges",      "url": "https://www.frontendmentor.io/challenges"},
        ],
        "hours": 15, "certificate": "Meta Front-End Developer Certificate",
        "project": "Build a job board dashboard with live API"
    },
    "Node.js": {
        "steps": [
            "1. Understand the event loop and async/await (2h)",
            "2. Build a REST API with Express.js (3h)",
            "3. Connect to MongoDB or PostgreSQL (2h)",
            "4. Add authentication (JWT) and write tests (3h)"
        ],
        "resources": [
            {"type": "docs",     "title": "Node.js Official Guides",            "url": "https://nodejs.org/en/docs/guides"},
            {"type": "course",   "title": "The Odin Project Full Stack JS",     "url": "https://www.theodinproject.com/paths/full-stack-javascript"},
            {"type": "practice", "title": "exercism.io Node.js Track",          "url": "https://exercism.org/tracks/javascript"},
        ],
        "hours": 12, "certificate": "OpenJS Node.js Services Developer",
        "project": "REST API with JWT auth + Swagger documentation"
    },
    "Git": {
        "steps": [
            "1. Learn init, add, commit, push, pull basics (1h)",
            "2. Understand branching, merging, and rebasing (1h)",
            "3. Practice pull requests and code review workflow (1h)",
            "4. Contribute to an open-source repo (ongoing)"
        ],
        "resources": [
            {"type": "docs",     "title": "Pro Git Book (free)",          "url": "https://git-scm.com/book/en/v2"},
            {"type": "course",   "title": "GitHub Learning Lab",          "url": "https://github.com/apps/github-learning-lab"},
            {"type": "practice", "title": "Learn Git Branching (visual)", "url": "https://learngitbranching.js.org"},
        ],
        "hours": 4, "certificate": "GitHub Foundations Certificate",
        "project": "Contribute a fix to an open-source project on GitHub"
    },
    "JavaScript": {
        "steps": [
            "1. Master: variables, closures, prototypes, async/await (4h)",
            "2. Learn DOM manipulation and browser APIs (2h)",
            "3. Study ES6+ features: spread, destructuring, modules (2h)",
            "4. Build a mini-project: weather app or quiz game (3h)"
        ],
        "resources": [
            {"type": "docs",     "title": "MDN JavaScript Guide",              "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide"},
            {"type": "course",   "title": "JavaScript.info (comprehensive)",   "url": "https://javascript.info"},
            {"type": "practice", "title": "freeCodeCamp JS Algorithms",        "url": "https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures/"},
        ],
        "hours": 10, "certificate": "freeCodeCamp JS Algorithms & Data Structures",
        "project": "Build a weather dashboard using fetch() API"
    },
    "Flask": {
        "steps": [
            "1. Learn Flask routing, templates, and request handling (2h)",
            "2. Build a REST API with JSON responses (2h)",
            "3. Connect Flask to a database (SQLite or PostgreSQL) (2h)",
            "4. Add authentication and deploy to a cloud platform (3h)"
        ],
        "resources": [
            {"type": "docs",     "title": "Flask Official Documentation",      "url": "https://flask.palletsprojects.com/en/latest/"},
            {"type": "course",   "title": "CS50 Web Flask Section",            "url": "https://cs50.harvard.edu/web/2020/weeks/7/"},
            {"type": "practice", "title": "Miguel Grinberg Flask Mega-Tutorial","url": "https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world"},
        ],
        "hours": 10, "certificate": "Python Web Development (Coursera)",
        "project": "Full-stack web app with Flask backend and user auth"
    },
    "Django": {
        "steps": [
            "1. Learn Django project structure, settings, and URLs (2h)",
            "2. Build models, views, and templates (3h)",
            "3. Use Django REST Framework for API endpoints (3h)",
            "4. Add authentication and deploy on Heroku/Railway (3h)"
        ],
        "resources": [
            {"type": "docs",     "title": "Django Official Tutorial",         "url": "https://docs.djangoproject.com/en/stable/intro/tutorial01/"},
            {"type": "course",   "title": "Django for Beginners (Book)",      "url": "https://djangoforbeginners.com"},
            {"type": "practice", "title": "Django Girls Tutorial",            "url": "https://tutorial.djangogirls.org"},
        ],
        "hours": 15, "certificate": "Meta Back-End Developer Certificate",
        "project": "Build a social media API with DRF"
    },
    "MongoDB": {
        "steps": [
            "1. Understand documents, collections, and BSON (1h)",
            "2. Practice CRUD operations and aggregation pipeline (3h)",
            "3. Design schemas for real-world use cases (2h)",
            "4. Connect MongoDB to a Node.js or Python app (2h)"
        ],
        "resources": [
            {"type": "docs",     "title": "MongoDB University (Free)",     "url": "https://learn.mongodb.com"},
            {"type": "course",   "title": "MongoDB Full Course (Traversy)","url": "https://www.youtube.com/watch?v=-56x56UppqQ"},
            {"type": "practice", "title": "MongoDB Atlas Free Tier",       "url": "https://www.mongodb.com/cloud/atlas"},
        ],
        "hours": 8, "certificate": "MongoDB Associate Developer",
        "project": "Build a REST API with Express + MongoDB Atlas"
    },
}

# Generic fallback resources for unknown skills
def _generic_resources(skill: str) -> dict:
    """Generate generic resource links for any skill not in _SKILL_RESOURCES."""
    q = requests.utils.quote(skill + " tutorial")
    return {
        "steps": [
            f"1. Read the official documentation for {skill} (2h)",
            f"2. Complete a beginner tutorial or crash course (3h)",
            f"3. Build a small hands-on project using {skill} (5h)",
            f"4. Solve practice problems or contribute to a related open-source project (ongoing)"
        ],
        "resources": [
            {"type": "docs",     "title": f"{skill} Official Docs",                     "url": f"https://www.google.com/search?q={q}+official+docs"},
            {"type": "course",   "title": f"freeCodeCamp {skill} Tutorial (YouTube)",   "url": f"https://www.youtube.com/results?search_query={q}+full+course"},
            {"type": "practice", "title": f"Practice {skill} on Kaggle or LeetCode",    "url": f"https://www.google.com/search?q={q}+practice+problems"},
        ],
        "hours": 10,
        "certificate": "",
        "project": f"Build a hands-on project demonstrating {skill}"
    }


# ------------------------------------------------------------------
# Ollama: generate personalized skill roadmap (with hard timeout)
# FIX 3: Updated prompt to generate step-by-step prep paths
# ------------------------------------------------------------------
def _call_ollama(
    missing_skills: list,
    match_score: float,
    resume=None,
    job_context=None,
    timeout: float = 35.0
) -> dict | None:
    """Call local Ollama to generate a rich, structured career roadmap."""
    # FIX 2: Use auto-detected model
    try:
        from models.llm_resume_parser import _detect_models
        _, model = _detect_models()  # use fallback/secondary for recommendations (lighter task)
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
    """FIX 3: Rich offline fallback using curated _SKILL_RESOURCES."""
    short_term_raw = []
    for s in (missing_skills[:5] if missing_skills else ["Core Skills"]):
        res = _SKILL_RESOURCES.get(s, _generic_resources(s))
        short_term_raw.append({
            "skill": s,
            "hours": res["hours"],
            "steps": res["steps"],
            "project": res["project"],
            "certificate": res["certificate"]
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
# Main entry point
# FIX 3: Enriches each short_term item with curated resources + steps
# FIX 4: YouTube runs with 5s timeout and limited to 3 search results
# ------------------------------------------------------------------
def generate_recommendations(
    missing_skills: list,
    match_score:    float,
    resume=None,
    job_context=None,
    ollama_timeout: float = 30.0,
) -> dict:
    """
    Generate a personalized learning roadmap with rich preparation paths.
    Each short_term item includes: steps, curated resources, project, certificate, and YouTube videos.
    """
    from concurrent.futures import ThreadPoolExecutor

    # ── Step 1: Ollama plan (with timeout) ─────────────────────────
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
    for item in short_term_raw[:5]:  # cap at 5 skills
        if isinstance(item, dict):
            skill = item.get("skill", "General")
        else:
            skill = str(item)
            item  = {"skill": skill, "hours": 10, "steps": [], "project": "", "certificate": ""}
        items.append((skill, item))

    # ── Step 2: Fetch YouTube videos for ALL skills in PARALLEL (FIX 4) ────
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
    }