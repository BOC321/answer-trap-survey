# In database.py

import sqlite3
import hashlib

DATABASE_FILE = "survey_app.db"

def initialize_database():
    # This function is correct and does not need changes.
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL)")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY, category_id INTEGER NOT NULL, text TEXT NOT NULL,
        answer1_text TEXT, answer1_score INTEGER, answer2_text TEXT, answer2_score INTEGER,
        answer3_text TEXT, answer3_score INTEGER, FOREIGN KEY (category_id) REFERENCES categories (id)
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS score_ranges (
        id INTEGER PRIMARY KEY, category_id INTEGER NOT NULL, start_score INTEGER NOT NULL,
        end_score INTEGER NOT NULL, report_text TEXT NOT NULL, display_color TEXT NOT NULL,
        FOREIGN KEY (category_id) REFERENCES categories (id)
    )""")
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        default_username = "admin"
        default_password = "password123"
        hashed_password = hashlib.sha256(default_password.encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (default_username, hashed_password))
    cursor.execute("SELECT id FROM categories WHERE name = '_TotalScore'")
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO categories (name) VALUES ('_TotalScore')")
    conn.commit()
    conn.close()

# --- All previous functions (save_setting, load_setting, etc.) are correct ---
def save_setting(key, value):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()
def load_setting(key):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None
def add_category(name):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"Category '{name}' already exists.")
    finally:
        conn.close()
def get_all_categories(include_total_score=False):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    query = "SELECT id, name FROM categories"
    if not include_total_score:
        query += " WHERE name != '_TotalScore'"
    else:
        query = query.replace("name", "REPLACE(name, '_TotalScore', 'Total Score') as display_name")
    cursor.execute(query)
    categories = cursor.fetchall()
    conn.close()
    return categories
def delete_category(category_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM score_ranges WHERE category_id = ?", (category_id,))
    cursor.execute("DELETE FROM questions WHERE category_id = ?", (category_id,))
    cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()
    conn.close()
def add_question(category_id, text, a1_text, a1_score, a2_text, a2_score, a3_text, a3_score):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO questions (category_id, text, answer1_text, answer1_score, answer2_text, answer2_score, answer3_text, answer3_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (category_id, text, a1_text, a1_score, a2_text, a2_score, a3_text, a3_score))
    conn.commit()
    conn.close()
def get_questions_for_category(category_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, text FROM questions WHERE category_id = ?", (category_id,))
    questions = cursor.fetchall()
    conn.close()
    return questions
def delete_question(question_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    conn.commit()
    conn.close()
def add_score_range(category_id, start_score, end_score, report_text, display_color):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO score_ranges (category_id, start_score, end_score, report_text, display_color)
        VALUES (?, ?, ?, ?, ?)
    """, (category_id, start_score, end_score, report_text, display_color))
    conn.commit()
    conn.close()
def get_ranges_for_category(category_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, start_score, end_score, report_text, display_color FROM score_ranges WHERE category_id = ? ORDER BY start_score", (category_id,))
    ranges = cursor.fetchall()
    conn.close()
    return ranges
def delete_score_range(range_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM score_ranges WHERE id = ?", (range_id,))
    conn.commit()
    conn.close()
def update_score_range(range_id, start_score, end_score, report_text, display_color):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE score_ranges
        SET start_score = ?, end_score = ?, report_text = ?, display_color = ?
        WHERE id = ?
    """, (start_score, end_score, report_text, display_color, range_id))
    conn.commit()
    conn.close()
def get_question_details(question_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
    question = cursor.fetchone()
    conn.close()
    return question
def update_question(q_id, text, a1_text, a1_score, a2_text, a2_score, a3_text, a3_score):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE questions
        SET text = ?, answer1_text = ?, answer1_score = ?, 
            answer2_text = ?, answer2_score = ?, answer3_text = ?, answer3_score = ?
        WHERE id = ?
    """, (text, a1_text, a1_score, a2_text, a2_score, a3_text, a3_score, q_id))
    conn.commit()
    conn.close()

# --- THIS IS THE NEW FUNCTION THAT WAS MISSING ---
def load_full_survey():
    """Loads all questions from all non-special categories for the user survey."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    # Join questions and categories to get category name, and filter out the special _TotalScore category
    cursor.execute("""
        SELECT q.id, q.category_id, q.text, 
               q.answer1_text, q.answer1_score, 
               q.answer2_text, q.answer2_score, 
               q.answer3_text, q.answer3_score,
               c.name as category_name
        FROM questions q
        JOIN categories c ON q.category_id = c.id
        WHERE c.name != '_TotalScore'
	ORDER BY c.id, q.id
    """)
    # We will add ordering later if needed (e.g., by category)
    survey_questions = cursor.fetchall()
    conn.close()
    return survey_questions