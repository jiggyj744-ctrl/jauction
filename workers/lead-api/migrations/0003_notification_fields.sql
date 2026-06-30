ALTER TABLE leads ADD COLUMN notification_status TEXT NOT NULL DEFAULT 'not_configured';
ALTER TABLE leads ADD COLUMN notification_channel TEXT;
ALTER TABLE leads ADD COLUMN notified_at TEXT;
ALTER TABLE leads ADD COLUMN notification_error TEXT;

CREATE INDEX IF NOT EXISTS idx_leads_notification_status ON leads(notification_status);
