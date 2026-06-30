CREATE TABLE IF NOT EXISTS leads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  source_url TEXT NOT NULL,
  name TEXT NOT NULL,
  phone TEXT NOT NULL,
  lead_type TEXT NOT NULL,
  case_or_address TEXT,
  share_ratio TEXT,
  owners TEXT,
  property_status TEXT,
  message TEXT,
  privacy_agree INTEGER NOT NULL DEFAULT 0,
  user_agent TEXT,
  ip_hash TEXT,
  review_status TEXT NOT NULL DEFAULT 'new'
);

CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at);
CREATE INDEX IF NOT EXISTS idx_leads_review_status ON leads(review_status);
CREATE INDEX IF NOT EXISTS idx_leads_ip_hash_created_at ON leads(ip_hash, created_at);
