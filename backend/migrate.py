"""
Migration script: Apply schema_v2.sql to the existing database.
Run: python migrate.py
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import psycopg
from psycopg.rows import dict_row

def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set in .env")
        sys.exit(1)

    schema_path = os.path.join(os.path.dirname(__file__), "..", "schema_v2.sql")
    schema_path = os.path.abspath(schema_path)

    if not os.path.exists(schema_path):
        print(f"ERROR: Schema file not found at {schema_path}")
        sys.exit(1)

    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()

    print(f"Connecting to database...")
    try:
        with psycopg.connect(db_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                print(f"Applying schema_v2.sql...")
                cur.execute(sql)
                conn.commit()
                print("[OK] Schema migration complete!")

                # Verify tables
                cur.execute("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                tables = [r["table_name"] for r in cur.fetchall()]
                print(f"\nTables in DB: {', '.join(tables)}")

                # Count linemen
                cur.execute("SELECT COUNT(*) as cnt FROM linemen")
                row = cur.fetchone()
                print(f"Linemen seeded: {row['cnt']}")

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
