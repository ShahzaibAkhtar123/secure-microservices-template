-- ============================================================
-- DATABASE INITIALIZATION
-- Creates additional database objects
-- ============================================================

-- Create audit log table for security tracking
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action VARCHAR(50) NOT NULL,
    details JSONB,
    ip_address INET,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create function to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for users table
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users') THEN
        DROP TRIGGER IF EXISTS update_users_updated_at ON users;
        CREATE TRIGGER update_users_updated_at 
            BEFORE UPDATE ON users 
            FOR EACH ROW 
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Create view for user summary
CREATE OR REPLACE VIEW user_summary AS
SELECT 
    id,
    username,
    email,
    created_at,
    EXTRACT(DAY FROM (CURRENT_TIMESTAMP - created_at)) AS days_since_joined
FROM users;

-- Grant permissions
GRANT SELECT ON user_summary TO myapp_user;
