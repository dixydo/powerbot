-- Create logs table for tracking bot activity
CREATE TABLE IF NOT EXISTS activity_logs (
    id BIGSERIAL PRIMARY KEY,
    action VARCHAR(50) NOT NULL,           -- 'status_request', 'subscribe', 'unsubscribe', 'notification_sent'
    user_id BIGINT,                        -- Telegram user ID (NULL for system notifications)
    details TEXT,                          -- Additional details (JSON or text)
    recipients_count INTEGER DEFAULT 0,    -- Number of recipients for notifications
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_activity_logs_action ON activity_logs(action);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created_at ON activity_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id ON activity_logs(user_id);
