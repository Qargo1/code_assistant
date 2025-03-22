import psycopg2
from psycopg2.extras import Json
from datetime import datetime
import json

class DatabaseManager:
    def __init__(self, dbname="code_analysis", user="postgres", password="postgres", host="localhost", port="5432"):
        self.conn_params = {
            "dbname": dbname,
            "user": user,
            "password": password,
            "host": host,
            "port": port
        }
        self._init_db()

    def _init_db(self):
        """Initialize database and create necessary tables if they don't exist."""
        try:
            conn = psycopg2.connect(**self.conn_params)
            cur = conn.cursor()
            
            # Create tables
            cur.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id SERIAL PRIMARY KEY,
                    path TEXT UNIQUE NOT NULL,
                    language TEXT NOT NULL,
                    last_analyzed TIMESTAMP,
                    metadata JSONB
                );
                
                CREATE TABLE IF NOT EXISTS dependencies (
                    id SERIAL PRIMARY KEY,
                    source_file_id INTEGER REFERENCES files(id),
                    target_file_id INTEGER REFERENCES files(id),
                    dep_type TEXT NOT NULL,
                    metadata JSONB,
                    UNIQUE(source_file_id, target_file_id, dep_type)
                );
                
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id SERIAL PRIMARY KEY,
                    file_id INTEGER REFERENCES files(id),
                    analysis_type TEXT NOT NULL,
                    result JSONB,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            conn.commit()
        except Exception as e:
            print(f"<error>Database initialization failed: {str(e)}</error>")
            raise
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

    def add_file(self, path, language, metadata=None):
        """Add or update a file in the database."""
        try:
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO files (path, language, last_analyzed, metadata)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (path) DO UPDATE
                        SET language = EXCLUDED.language,
                            last_analyzed = EXCLUDED.last_analyzed,
                            metadata = EXCLUDED.metadata
                        RETURNING id
                    """, (path, language, datetime.now(), Json(metadata or {})))
                    return cur.fetchone()[0]
        except Exception as e:
            print(f"<error>Failed to add file: {str(e)}</error>")
            raise

    def add_dependency(self, source_path, target_path, dep_type, metadata=None):
        """Add a dependency between two files."""
        try:
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        WITH source AS (
                            SELECT id FROM files WHERE path = %s
                        ), target AS (
                            SELECT id FROM files WHERE path = %s
                        )
                        INSERT INTO dependencies (source_file_id, target_file_id, dep_type, metadata)
                        SELECT source.id, target.id, %s, %s
                        FROM source, target
                        ON CONFLICT (source_file_id, target_file_id, dep_type) DO UPDATE
                        SET metadata = EXCLUDED.metadata
                    """, (source_path, target_path, dep_type, Json(metadata or {})))
        except Exception as e:
            print(f"<error>Failed to add dependency: {str(e)}</error>")
            raise

    def store_analysis_result(self, file_path, analysis_type, result):
        """Store analysis results for a file."""
        try:
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        WITH file_id AS (
                            SELECT id FROM files WHERE path = %s
                        )
                        INSERT INTO analysis_results (file_id, analysis_type, result)
                        SELECT id, %s, %s
                        FROM file_id
                    """, (file_path, analysis_type, Json(result)))
        except Exception as e:
            print(f"<error>Failed to store analysis result: {str(e)}</error>")
            raise

    def get_file_analysis(self, file_path, analysis_type=None):
        """Retrieve analysis results for a file."""
        try:
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT ar.analysis_type, ar.result, ar.timestamp
                        FROM analysis_results ar
                        JOIN files f ON ar.file_id = f.id
                        WHERE f.path = %s
                    """
                    params = [file_path]
                    if analysis_type:
                        query += " AND ar.analysis_type = %s"
                        params.append(analysis_type)
                    query += " ORDER BY ar.timestamp DESC"
                    cur.execute(query, params)
                    return cur.fetchall()
        except Exception as e:
            print(f"<error>Failed to retrieve analysis: {str(e)}</error>")
            raise

    def get_dependencies(self, file_path, dep_type=None):
        """Get dependencies for a file."""
        try:
            with psycopg2.connect(**self.conn_params) as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT f2.path, d.dep_type, d.metadata
                        FROM dependencies d
                        JOIN files f1 ON d.source_file_id = f1.id
                        JOIN files f2 ON d.target_file_id = f2.id
                        WHERE f1.path = %s
                    """
                    params = [file_path]
                    if dep_type:
                        query += " AND d.dep_type = %s"
                        params.append(dep_type)
                    cur.execute(query, params)
                    return cur.fetchall()
        except Exception as e:
            print(f"<error>Failed to retrieve dependencies: {str(e)}</error>")
            raise
