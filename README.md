# Job Fit Analyzer

A premium, intelligent web application that analyzes resume data and evaluates job fit using advanced Natural Language Processing (NLP) and Large Language Models (LLMs). The application extracts key details (skills, work experience, projects, education, certifications) from uploaded resumes and matches them semantically against predefined job roles to calculate matching scores.

## 🚀 Key Features

*   **Intelligent Resume Parsing**: Utilizes LLMs (via local Ollama integrations like `qwen2.5` or `llama3`) and spaCy-based NLP models (like JobBERT) to extract structured details from PDF resumes reliably.
*   **ATS Scoring & Evaluation**: Calculates multiple scores:
    *   *Semantic Similarity Score* (using Sentence-Transformers/SBERT)
    *   *Skills Match Score*
    *   *Experience Match Score*
    *   *Projects Match Score*
    *   *Education & Certification Match Score*
*   **Premium Web Dashboard**: A modern, glassmorphic UI styled with custom vanilla CSS and dynamic micro-animations for an interactive and high-end experience.
*   **Dynamic Status Updates**: Live backend parsing status messages displayed to the user during evaluation.
*   **Secure Authentication**: User registration, login, and session management.
*   **Job Role Management**: Interactive portal to define and view job role criteria.

## 🛠️ Tech Stack

### Backend
*   **Framework**: Flask (Python)
*   **Database**: Fluxbase (PostgreSQL/SQL via API)
*   **NLP & AI**:
    *   spaCy (`en_core_web_sm` / JobBERT for skill extraction)
    *   Sentence-Transformers (SBERT for embeddings)
    *   Ollama (Local LLM APIs for precise section-based parsing)
*   **PDF Extraction**: `pdfplumber`, `pdfminer.six`, `pypdfium2`

### Frontend
*   **Core**: HTML5, Vanilla JavaScript, Vanilla CSS
*   **Theme**: Dark Mode with rich gradients and micro-animations

---

## 💻 Installation & Setup

### Prerequisites
*   Python 3.10+
*   [Ollama](https://ollama.com/) (running locally with `qwen2.5:7b-instruct` or `llama3`)

### 1. Clone & Navigate
```bash
git clone https://github.com/Lalith-Tejas-M/Job-Fit-Analyzer.git
cd Job-Fit-Analyzer
```

### 2. Configure Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate      # On Windows
source venv/bin/activate   # On macOS/Linux
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Ollama
Make sure Ollama is running and has the model pulled:
```bash
ollama run qwen2.5:7b-instruct
# OR fallback:
ollama run llama3
```

### 5. Start the Flask Backend
```bash
python Backend/app.py
```

### 6. Access the Frontend
Open `Frontend/index.html` or serve the `Frontend/` folder using any local web server (e.g., Live Server in VS Code, or `python -m http.server` from the Frontend directory).

---

