ALTER TABLE leads ADD COLUMN admin_note TEXT;
ALTER TABLE leads ADD COLUMN updated_at TEXT;

CREATE INDEX IF NOT EXISTS idx_leads_updated_at ON leads(updated_at);
