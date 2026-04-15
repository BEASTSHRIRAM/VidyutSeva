import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS areas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS outages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    area_name VARCHAR(255) NOT NULL,
    outage_type VARCHAR(100),
    reason TEXT,
    status VARCHAR(50) DEFAULT 'active',
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE,
    source VARCHAR(100),
    severity INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS call_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    caller_area VARCHAR(255),
    user_message TEXT,
    ai_response TEXT,
    outage_found BOOLEAN,
    diagnosis_type VARCHAR(100),
    call_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crowd_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    area_name VARCHAR(255) NOT NULL,
    description TEXT,
    reporter_phone VARCHAR(50),
    report_source VARCHAR(100) DEFAULT 'web',
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255),
    area_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    phone_number VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS alert_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID REFERENCES alert_subscriptions(id),
    outage_id UUID,
    message TEXT,
    status VARCHAR(50) DEFAULT 'sent',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert dummy data
INSERT INTO areas (name) VALUES ('Koramangala'), ('Indiranagar'), ('Whitefield'), ('Jayanagar') ON CONFLICT (name) DO NOTHING;

INSERT INTO outages (area_name, outage_type, reason, source) 
SELECT 'Koramangala', 'maintenance', 'Transformer replacement', 'bescom' 
WHERE NOT EXISTS (SELECT 1 FROM outages WHERE area_name = 'Koramangala' AND status='active');
"""

def init_db():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set")
        return
        
    print("Connecting to db...")
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            print("Executing schema setup...")
            cur.execute(SCHEMA_SQL)
            conn.commit()
            print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()
