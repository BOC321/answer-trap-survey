# In auth.py

import streamlit as st
import sqlite3
import hashlib
from database import DATABASE_FILE

def check_password(username, password):
    """Checks if the username and password are correct."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # Hash the provided password to compare with the stored hash
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()

    if result and result[0] == password_hash:
        return True
    return False

def login_form():
    """Displays the login form and handles the logic."""
    st.header("Admin Login")
    with st.form("login_form"):
        username = st.text_input("Username").lower()
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if check_password(username, password):
                st.session_state.logged_in = True
                # This command tells Streamlit to re-run the script from the top
                st.rerun() 
            else:
                st.error("The username or password you entered is incorrect.")