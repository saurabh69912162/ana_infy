import sqlite3
import time
def get_db_connection():
    conn = sqlite3.connect('requests.db')
    conn.row_factory = sqlite3.Row  # Enable dictionary-like access to rows
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Create the requests table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        development_center TEXT,
        query_text TEXT,
        status TEXT,
        topic TEXT,
        main_issue TEXT,
        category TEXT,
        agent_name TEXT,
        logs TEXT,
        escalated BOOLEAN DEFAULT 0,
        assigned_to TEXT,
        resolution TEXT,
        severity TEXT,
        urgency TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        closing_time TIMESTAMP DEFAULT NULL,
        time_taken INTEGER DEFAULT NULL,
        extra_fields TEXT DEFAULT NULL
    )
    ''')
    # Create the comments table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER,
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (request_id) REFERENCES requests (id)
    )
    ''')
    # Create the knowledgebase table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS knowledgebase (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        issue_description TEXT,
        resolution TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    # Create the feedback table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER,
        points INTEGER,
        feedback_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ticket_id) REFERENCES requests (id)
    )
    ''')
    conn.commit()
    conn.close()


def insert_comment(request_id, comment):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO comments (request_id, comment)
    VALUES (?, ?)
    ''', (request_id, comment))
    conn.commit()
    conn.close()

def insert_request(name, email, development_center, query_text, status, topic, main_issue, category, agent_name,severity,urgency,resolution):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO requests (name, email, development_center, query_text, status, topic, main_issue, category, agent_name,severity,urgency,resolution)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, email, development_center, query_text, status, topic, main_issue, category, agent_name,severity,urgency,resolution))
    conn.commit()
    request_id = cursor.lastrowid
    conn.close()
    return request_id

def get_all_requests():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM requests ORDER BY created_at DESC')
    requests = cursor.fetchall()
    conn.close()
    return requests 

def toggle_ticket_status(ticket_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT status FROM requests WHERE id = ?', (ticket_id,))
    current_status = cursor.fetchone()['status']
    new_status = 'Closed' if current_status == 'Open' else 'Open'
    cursor.execute('UPDATE requests SET status = ? WHERE id = ?', (new_status, ticket_id))
    conn.commit()
    conn.close()
    return True



def get_ticket_details(ticket_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM requests WHERE id = ?', (ticket_id,))
    ticket = cursor.fetchone()
    conn.close()
    return ticket