"""
Quick validation script for jjzha/jobbert_skill_extraction.
Run this ONCE before starting the Flask server to:
  1. Trigger the model download (~440MB, one-time only)
  2. Verify multi-word skill extraction works correctly
  3. Compare against the old dslim/bert-base-NER behaviour

Usage:
    cd "c:\\Users\\tejas\\OneDrive\\Desktop\\Machine Learning\\ML project"
    python scratch\\test_jobbert.py
"""

from transformers import pipeline

RESUME_SAMPLE = """
Implemented Natural Language Processing techniques for summarization and classification.
Built a spam vs ham classifier using NLP and Machine Learning.
Developed an AI-powered platform using PyTorch, Scikit-learn, NumPy, and Pandas.
Proficient in Python, Java, SQL, and JavaScript.
Used Docker, Kubernetes, AWS for deployment.
Integrated LangChain for Agentic AI workflows.
Experience with TensorFlow, Keras, OpenCV, and HuggingFace transformers.
"""

print("=" * 60)
print("Loading jjzha/jobbert_skill_extraction ...")
print("(First run downloads ~440MB — please wait)")
print("=" * 60)

ner = pipeline(
    "token-classification",
    model="jjzha/jobbert_skill_extraction",
    aggregation_strategy="first",
    device=-1,
)

print("\nModel loaded. Running inference...\n")

results = ner(RESUME_SAMPLE)

print(f"{'Entity':<40} {'Score':>6}  Label")
print("-" * 55)
for ent in results:
    word  = ent["word"].replace("##", "").strip()
    score = ent["score"]
    label = ent.get("entity_group", ent.get("entity", "?"))
    # Only show high-confidence SKILL entities
    if score >= 0.70:
        print(f"{word:<40} {score:>6.2f}  {label}")

print("\n" + "=" * 60)
print("Expected to see as SINGLE entities (not fragmented):")
expected = [
    "Natural Language Processing",
    "Machine Learning",
    "PyTorch",
    "Scikit-learn",
    "NumPy",
    "Pandas",
    "Python",
    "Java",
    "SQL",
    "JavaScript",
    "Docker",
    "Kubernetes",
    "AWS",
    "LangChain",
    "TensorFlow",
    "Keras",
    "OpenCV",
]
for e in expected:
    print(f"  - {e}")
print("=" * 60)
print("If these appear as whole tokens above, the model works correctly.")
print("You can now restart the Flask server.")
