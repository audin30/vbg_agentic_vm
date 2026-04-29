-- Identity-linked Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT NOT NULL,
    action TEXT NOT NULL,
    request_data JSONB,
    response_summary TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Knowledge Cache for TI Lookups
CREATE TABLE IF NOT EXISTS knowledge_cache (
    indicator TEXT PRIMARY KEY,
    indicator_type TEXT NOT NULL,
    cached_result JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Persistent User Active Queries (Tabs)
CREATE TABLE IF NOT EXISTS user_active_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT NOT NULL,
    title TEXT NOT NULL,
    query_state JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Human-in-the-Loop Feedback
CREATE TABLE IF NOT EXISTS agent_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT NOT NULL,
    action_type TEXT NOT NULL,          -- e.g., 'remediation', 'prioritization'
    target TEXT NOT NULL,               -- e.g., '10.0.0.5', 'CVE-2024-1234'
    decision TEXT NOT NULL,             -- 'approved', 'denied'
    feedback_notes TEXT,                -- 'Do not patch this production server during business hours'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Local Users Fallback
CREATE TABLE IF NOT EXISTS local_users (
    username TEXT PRIMARY KEY,
    hashed_password TEXT NOT NULL,
    full_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
