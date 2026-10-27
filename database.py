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

def get_database_path(db_path=None):
    """Returns target SQLite file path, using writable /tmp on Vercel if SQLite is used."""
    if db_path:
        return db_path
    if os.environ.get('VERCEL') == '1' and not is_using_postgres():
        tmp_db = '/tmp/bloodconnect.db'
        if not os.path.exists(tmp_db) and os.path.exists(DATABASE_PATH):
            import shutil
            try:
                shutil.copy2(DATABASE_PATH, tmp_db)
            except Exception:
                pass
        return tmp_db
    return DATABASE_PATH

def get_database_url():
    """Read common managed-Postgres environment variable names."""
    for key in ('DATABASE_URL', 'POSTGRES_URL', 'POSTGRES_PRISMA_URL', 'POSTGRES_URL_NON_POOLING', 'SUPABASE_DB_URL'):
        value = (os.environ.get(key) or '').strip()
        if value:
            # If remote PostgreSQL and sslmode is not explicitly configured, enforce sslmode=require
            if ('localhost' not in value and '127.0.0.1' not in value) and 'sslmode=' not in value:
                separator = '&' if '?' in value else '?'
                value = f"{value}{separator}sslmode=require"
            return value
    return ''

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
        target_path = get_database_path(db_path)
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
            ensure_blood_bank_tables(conn, cur, postgres=True)
            conn.commit()
        else:
            with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
                conn.executescript(f.read())
            conn.commit()
            ensure_blood_bank_tables(conn, cur, postgres=False)
            conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        cur.close()
        if not in_ctx and conn:
            conn.close()

def ensure_blood_bank_tables(conn=None, cur=None, postgres=None):
    """Create the additive blood-bank inventory tables without touching existing data."""
    own_connection = conn is None
    own_cursor = cur is None
    if own_connection:
        conn = get_db()
    if own_cursor:
        cur = conn.cursor()
    if postgres is None:
        postgres = is_using_postgres()

    id_type = 'SERIAL PRIMARY KEY' if postgres else 'INTEGER PRIMARY KEY AUTOINCREMENT'
    bool_type = 'BOOLEAN NOT NULL DEFAULT FALSE' if postgres else 'INTEGER NOT NULL DEFAULT 0 CHECK (is_verified IN (0, 1))'
    stock_id_type = 'SERIAL PRIMARY KEY' if postgres else 'INTEGER PRIMARY KEY AUTOINCREMENT'
    statements = [
        f'''CREATE TABLE IF NOT EXISTS blood_banks (
            id {id_type},
            name VARCHAR(160) NOT NULL,
            email VARCHAR(160) NOT NULL UNIQUE,
            phone VARCHAR(40) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            license_number VARCHAR(100) NOT NULL,
            city VARCHAR(100) NOT NULL,
            address TEXT NOT NULL,
            latitude DOUBLE PRECISION DEFAULT 13.0827,
            longitude DOUBLE PRECISION DEFAULT 80.2707,
            is_verified {bool_type},
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )''',
        f'''CREATE TABLE IF NOT EXISTS blood_bank_stock (
            id {stock_id_type},
            blood_bank_id INTEGER NOT NULL REFERENCES blood_banks(id) ON DELETE CASCADE,
            blood_group VARCHAR(5) NOT NULL CHECK (blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
            component VARCHAR(40) NOT NULL CHECK (component IN ('Whole Blood', 'Red Cells', 'Platelets', 'Plasma')),
            units_available INTEGER NOT NULL DEFAULT 0 CHECK (units_available >= 0),
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (blood_bank_id, blood_group, component)
        )''',
    ]
    if postgres:
        statements.extend([
            'ALTER TABLE blood_banks ENABLE ROW LEVEL SECURITY',
            'ALTER TABLE blood_bank_stock ENABLE ROW LEVEL SECURITY',
        ])
    try:
        for statement in statements:
            try:
                cur.execute(statement)
                conn.commit()
            except Exception:
                conn.rollback()
                # Ignore non-fatal DDL errors (such as RLS privilege or already active)
                if 'ROW LEVEL SECURITY' not in statement:
                    raise
    finally:
        if own_cursor:
            cur.close()
        if own_connection and not has_app_context():
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
