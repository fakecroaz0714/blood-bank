import os
import re
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
                os.environ[k.strip()] = v.strip()

DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bloodconnect.db')
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')
SCHEMA_PG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema_supabase.sql')

def get_database_url():
    """Dynamically get the current DATABASE_URL from environment."""
    return (os.environ.get('DATABASE_URL') or '').strip()

def is_using_postgres():
    db_url = get_database_url()
    return bool(db_url and db_url.startswith(('postgresql://', 'postgres://')))

def get_db(db_path=None):
    """Get database connection for current context (Postgres or SQLite)."""
    if has_app_context() and hasattr(g, 'db'):
        return g.db

    if is_using_postgres():
        import psycopg2
        import psycopg2.extras
        db_url = get_database_url()
        conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
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

def _normalize_pg_query(query):
    """Translates SQLite-style queries to Postgres syntax and handles boolean column checks."""
    pg_query = query.replace('?', '%s')
    pg_query = re.sub(r'\b(is_verified|is_available|is_read)\s*=\s*1\b', r'\1 = TRUE', pg_query, flags=re.IGNORECASE)
    pg_query = re.sub(r'\b(is_verified|is_available|is_read)\s*=\s*0\b', r'\1 = FALSE', pg_query, flags=re.IGNORECASE)
    return pg_query

def init_db(db_path=None):
    """Initialize database tables."""
    in_ctx = has_app_context()
    conn = get_db(db_path)
    cur = conn.cursor()
    try:
        if is_using_postgres():
            with open(SCHEMA_PG_PATH, 'r', encoding='utf-8') as f:
                cur.execute(f.read())
            conn.commit()
        else:
            with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
                conn.executescript(f.read())
            conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        cur.close()
        if not in_ctx and conn:
            conn.close()

def query_db(query, args=(), one=False, db_path=None):
    """Execute a SELECT query and return rows as dictionary-like objects."""
    in_ctx = has_app_context()
    conn = get_db(db_path)
    cur = conn.cursor()
    try:
        if is_using_postgres():
            pg_query = _normalize_pg_query(query)
            cur.execute(pg_query, args)
            rows = cur.fetchall()
            return (rows[0] if rows else None) if one else rows
        else:
            cur.execute(query, args)
            rows = cur.fetchall()
            return (rows[0] if rows else None) if one else rows
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        cur.close()
        if not in_ctx and conn:
            conn.close()

def execute_db(query, args=(), db_path=None):
    """Execute an INSERT/UPDATE/DELETE query and commit. Returns lastrowid/id if applicable."""
    in_ctx = has_app_context()
    conn = get_db(db_path)
    cur = conn.cursor()
    try:
        if is_using_postgres():
            pg_query = _normalize_pg_query(query)
            trimmed = pg_query.strip().rstrip(';').strip()
            has_returning = 'RETURNING' in trimmed.upper()
            if trimmed.upper().startswith('INSERT') and not has_returning:
                pg_query = f"{trimmed} RETURNING id"
                cur.execute(pg_query, args)
                last_id_row = cur.fetchone()
                if last_id_row:
                    if isinstance(last_id_row, dict):
                        last_id = last_id_row.get('id')
                    elif isinstance(last_id_row, (list, tuple)):
                        last_id = last_id_row[0]
                    else:
                        last_id = getattr(last_id_row, 'id', None)
                else:
                    last_id = None
            else:
                cur.execute(pg_query, args)
                last_id = None
            conn.commit()
            return last_id
        else:
            cur.execute(query, args)
            conn.commit()
            return cur.lastrowid
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        cur.close()
        if not in_ctx and conn:
            conn.close()
