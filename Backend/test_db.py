import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import database
try:
    database.init_db()
    print("Database initialized successfully.")
except Exception as e:
    print(f"Error initializing database: {e}")
