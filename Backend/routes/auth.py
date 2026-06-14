from flask import Blueprint, request, jsonify, session
import bcrypt
import uuid
import database

# Inline security functions
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    
    if not all([name, email, password]):
        return jsonify({"error": "All fields required"}), 400
    
    user_id = database.generate_id()
    password_hash = hash_password(password)
    
    try:
        database.query('''
            INSERT INTO users (user_id, name, email, password_hash)
            VALUES (?, ?, ?, ?)
        ''', [user_id, name, email, password_hash])
        
        return jsonify({"message": "User registered", "user_id": user_id}), 201
    except Exception as e:
        if "duplicate key value" in str(e).lower() or "unique constraint" in str(e).lower() or "42P01" in str(e):
            return jsonify({"error": "Email already exists or error occurred"}), 409
        raise e

@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    rows = database.query('SELECT * FROM users WHERE email = ?', [email])
    user = rows[0] if rows else None
    
    if not user or not verify_password(password, user['password_hash']):
        return jsonify({"error": "Invalid credentials"}), 401
    
    # Return user data (in real app, use JWT or session)
    return jsonify({
        "message": "Login successful",
        "user_id": user['user_id'],
        "name": user['name'],
        "email": user['email']
    }), 200

@bp.route('/logout', methods=['POST'])
def logout():
    # In a real app, invalidate session/token
    return jsonify({"message": "Logged out"}), 200