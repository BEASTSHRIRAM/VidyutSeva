-- ============================================
-- VidyutSeva — Schema v2 (Additive)
-- New tables: users, complaints, complaint_upvotes, escalations, linemen
-- ============================================

-- Users (phone-based auth)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(15) UNIQUE NOT NULL,
    name VARCHAR(100),
    role TEXT DEFAULT 'citizen',            -- 'citizen', 'admin', 'lineman'
    is_verified BOOLEAN DEFAULT FALSE,
    otp_code VARCHAR(6),
    otp_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Linemen roster
CREATE TABLE IF NOT EXISTS linemen (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lineman_id VARCHAR(10) UNIQUE NOT NULL,  -- e.g. L001
    name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(15) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    area TEXT NOT NULL,
    division TEXT,                             -- 'South', 'North', 'East', 'West'
    shift TEXT DEFAULT 'Day',                  -- 'Day', 'Night'
    is_available BOOLEAN DEFAULT TRUE,
    last_assigned_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Complaints (citizen reports with upvote system)
CREATE TABLE IF NOT EXISTS complaints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    complaint_id VARCHAR(20) UNIQUE NOT NULL,  -- e.g. VSEVA-260416-7843
    phone_number VARCHAR(15),                   -- even anonymous calls have this
    user_id UUID REFERENCES users(id),          -- NULL until they sign up
    source TEXT DEFAULT 'app',                  -- 'vapi', 'app', 'x_scrape', 'web'
    text TEXT NOT NULL,
    area TEXT NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    fault_type TEXT,                             -- 'transformer', 'cable', 'pole', 'meter', 'other', NULL
    is_hardware_fault BOOLEAN DEFAULT FALSE,
    status TEXT DEFAULT 'new',                  -- 'new', 'acknowledged', 'assigned', 'in_progress', 'resolved'
    upvote_count INTEGER DEFAULT 0,
    escalated BOOLEAN DEFAULT FALSE,
    assigned_lineman_id UUID REFERENCES linemen(id),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Track who upvoted which complaint (prevent double-upvote)
CREATE TABLE IF NOT EXISTS complaint_upvotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    complaint_id UUID REFERENCES complaints(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(complaint_id, user_id)
);

-- Escalation records
CREATE TABLE IF NOT EXISTS escalations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    complaint_id UUID REFERENCES complaints(id),
    report_text TEXT,
    fault_type TEXT,
    confidence DOUBLE PRECISION,
    lineman_id UUID REFERENCES linemen(id),
    lineman_name TEXT,
    lineman_phone VARCHAR(15),
    distance_km DOUBLE PRECISION,
    vapi_call_id TEXT,                          -- Vapi call ID if call was triggered
    call_status TEXT DEFAULT 'pending',         -- 'pending', 'calling', 'answered', 'failed'
    status TEXT DEFAULT 'escalated',            -- 'escalated', 'acknowledged', 'dispatched', 'resolved'
    escalated_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_complaints_area ON complaints(area);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);
CREATE INDEX IF NOT EXISTS idx_complaints_upvotes ON complaints(upvote_count DESC);
CREATE INDEX IF NOT EXISTS idx_complaints_phone ON complaints(phone_number);
CREATE INDEX IF NOT EXISTS idx_escalations_status ON escalations(status);
CREATE INDEX IF NOT EXISTS idx_linemen_area ON linemen(area);
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number);

-- Seed linemen data
INSERT INTO linemen (lineman_id, name, phone_number, latitude, longitude, area, division, shift) VALUES
    ('L001', 'Ramesh Kumar',    '9886712345', 12.9716, 77.5946, 'HSR Layout',       'South', 'Day'),
    ('L002', 'Prakash Rao',     '9741256789', 12.9345, 77.6123, 'Koramangala',       'South', 'Day'),
    ('L003', 'Suresh Babu',     '8123498765', 13.0256, 77.5689, 'Yelahanka',         'North', 'Day'),
    ('L004', 'Ganesh Reddy',    '9845098765', 12.9784, 77.6408, 'Indiranagar',       'East',  'Day'),
    ('L005', 'Mahesh Gowda',    '7022345678', 12.9698, 77.7500, 'Whitefield',        'East',  'Night'),
    ('L006', 'Ravi Shankar',    '9632178901', 12.9900, 77.5520, 'Rajajinagar',       'West',  'Day'),
    ('L007', 'Venkatesh Murthy','8904567123', 13.0035, 77.5710, 'Malleshwaram',      'West',  'Night'),
    ('L008', 'Anil Kumar',      '9480123456', 12.9166, 77.6101, 'BTM Layout',        'South', 'Day'),
    ('L009', 'Srinivas Rao',    '8765432109', 12.8399, 77.6770, 'Electronic City',   'South', 'Night'),
    ('L010', 'Deepak Sharma',   '9342567890', 12.9591, 77.7009, 'Marathahalli',      'East',  'Day'),
    ('L011', 'Naveen Prasad',   '8612345678', 12.9308, 77.5838, 'Jayanagar',         'South', 'Day'),
    ('L012', 'Kiran Kumar',     '9901234567', 12.9255, 77.5468, 'Banashankari',      'South', 'Night'),
    ('L013', 'Manjunath HB',    '7899012345', 13.0070, 77.5810, 'Sadashivanagar',    'North', 'Day'),
    ('L014', 'Basavaraj Patil', '9845678901', 12.9710, 77.5330, 'Vijayanagar',       'West',  'Day'),
    ('L015', 'Harsha Vardhan',  '8456789012', 12.9260, 77.6760, 'Bellandur',         'East',  'Night')
ON CONFLICT (lineman_id) DO NOTHING;

-- Insert default admin user
INSERT INTO users (phone_number, name, role, is_verified) VALUES
    ('9999999999', 'BESCOM Admin', 'admin', TRUE)
ON CONFLICT (phone_number) DO NOTHING;
