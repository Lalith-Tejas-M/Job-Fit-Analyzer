# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys

# allow imports from sibling folders
sys.path.insert(0, os.path.dirname(__file__))

import database
from routes import auth, resume, analysis, settings, resume_review
from models.nlp_processor import get_nlp_model
from models.embeddings import model          # Sentence-BERT (loads once)

app = Flask(__name__)
CORS(app)  # Enable CORS for local frontend

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB limit

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ------------------------------------------------------------------
# One-time initialisation
# ------------------------------------------------------------------
database.init_db()

print("Loading NLP models...")
nlp         = get_nlp_model()   # spaCy + HuggingFace NER
embed_model = model             # Sentence-BERT
print("Models loaded successfully!")

# ------------------------------------------------------------------
# Register API blueprints
# ------------------------------------------------------------------
app.register_blueprint(auth.bp,           url_prefix='/api')
app.register_blueprint(resume.bp,         url_prefix='/api')
app.register_blueprint(analysis.bp,       url_prefix='/api')
app.register_blueprint(settings.bp,       url_prefix='/api')
app.register_blueprint(resume_review.bp,  url_prefix='/api')

# ------------------------------------------------------------------
# Frontend is now served by Next.js on port 3000 (npm run dev)
# This Flask server only handles /api/* routes
# ------------------------------------------------------------------

# ------------------------------------------------------------------
# Health check — lets frontend detect when models are fully loaded
# ------------------------------------------------------------------
@app.route('/api/health')
def health_check():
    return jsonify({"status": "ok", "models_loaded": True}), 200

# ------------------------------------------------------------------
# Run development server
# ------------------------------------------------------------------
if __name__ == '__main__':
    app.run(host='localhost', debug=True, port=5000)