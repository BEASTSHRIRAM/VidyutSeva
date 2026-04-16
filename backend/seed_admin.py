import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

def seed_admin():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("DATABASE_URL not found")
        return
    
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (phone_number, name, role) 
                VALUES ('9999999999', 'BESCOM Admin', 'admin') 
                ON CONFLICT (phone_number) 
                DO UPDATE SET role='admin', name='BESCOM Admin'
            """)
            conn.commit()
            print('[OK] Admin user seeded: 9999999999')

if __name__ == "__main__":
    seed_admin()
