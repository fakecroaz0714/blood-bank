import os
import sqlite3
from flask import g

DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bloodconnect.db')
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')

def get_db(db_path=None):
    """Get database connection for the current Flask request context or standalone."""
    target_path = db_path or DATABASE_PATH
    if g and hasattr(g, 'db'):
        return g.db

    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    
    if g:
        g.db = conn
    return conn

def close_db(e=None):
    """Close the database connection on request teardown."""
    db = g.pop('db', None) if g else None
    if db is not None:
        db.close()

def init_db(db_path=None):
    """Initialize database tables from schema.sql."""
    target_path = db_path or DATABASE_PATH
    conn = sqlite3.connect(target_path)
    conn.execute("PRAGMA foreign_keys = ON")
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

def query_db(query, args=(), one=False, db_path=None):
    """Execute a SELECT query and return rows as dictionary-like objects."""
    conn = get_db(db_path)
    cur = conn.cursor()
    cur.execute(query, args)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows

def execute_db(query, args=(), db_path=None):
    """Execute an INSERT/UPDATE/DELETE query and commit. Returns lastrowid."""
    conn = get_db(db_path)
    cur = conn.cursor()
    cur.execute(query, args)
    conn.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id
