import os
import sqlite3
from flask import g, has_app_context

# Load .env file if present
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(ENV_PATH):
    with open(ENV_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

DATABASE_URL = os.environ.get('DATABASE_URL')
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bloodconnect.db')
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')
SCHEMA_PG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema_supabase.sql')

def is_using_postgres():
    return bool(DATABASE_URL and DATABASE_URL.startswith(('postgresql://', 'postgres://')))

def get_db(db_path=None):
    """Get database connection for current context (Postgres or SQLite)."""
    if has_app_context() and hasattr(g, 'db'):
        return g.db

    if is_using_postgres():
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        target_path = db_path or DATABASE_PATH
        conn = sqlite3.connect(target_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

    if has_app_context():
        g.db = conn
    return conn

def close_db(e=None):
    """Close the database connection on request teardown."""
    if has_app_context():
        db = g.pop('db', None)
        if db is not None:
            db.close()

def init_db(db_path=None):
    """Initialize database tables."""
    if is_using_postgres():
        in_ctx = has_app_context()
        conn = get_db()
        cur = conn.cursor()
        try:
            with open(SCHEMA_PG_PATH, 'r', encoding='utf-8') as f:
                cur.execute(f.read())
            conn.commit()
        finally:
            cur.close()
            if not in_ctx:
                conn.close()
    else:
        target_path = db_path or DATABASE_PATH
        conn = sqlite3.connect(target_path)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
                conn.executescript(f.read())
            conn.commit()
        finally:
            conn.close()

def query_db(query, args=(), one=False, db_path=None):
    """Execute a SELECT query and return rows as dictionary-like objects."""
    in_ctx = has_app_context()
    conn = get_db(db_path)
    cur = conn.cursor()
    try:
        if is_using_postgres():
            pg_query = query.replace('?', '%s')
            cur.execute(pg_query, args)
            rows = cur.fetchall()
            return (rows[0] if rows else None) if one else rows
        else:
            cur.execute(query, args)
            rows = cur.fetchall()
            return (rows[0] if rows else None) if one else rows
    finally:
        cur.close()
        if not in_ctx:
            conn.close()

def execute_db(query, args=(), db_path=None):
    """Execute an INSERT/UPDATE/DELETE query and commit. Returns lastrowid if applicable."""
    in_ctx = has_app_context()
    conn = get_db(db_path)
    cur = conn.cursor()
    try:
        if is_using_postgres():
            pg_query = query.replace('?', '%s')
            trimmed = pg_query.strip()
            has_returning = 'RETURNING' in trimmed.upper()
            if trimmed.upper().startswith('INSERT') and not has_returning:
                pg_query = f"{trimmed} RETURNING id"
                cur.execute(pg_query, args)
                last_id_row = cur.fetchone()
                last_id = last_id_row['id'] if last_id_row else None
            else:
                cur.execute(pg_query, args)
                last_id = None
            conn.commit()
            return last_id
        else:
            cur.execute(query, args)
            conn.commit()
            return cur.lastrowid
    finally:
        cur.close()
        if not in_ctx:
            conn.close()
