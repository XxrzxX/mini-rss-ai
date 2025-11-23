-- Migration 001: Initial database schema
-- Create the chats table
CREATE TABLE IF NOT EXISTS chats (
    id UUID PRIMARY KEY,
    messages JSONB NOT NULL DEFAULT '[]',
    chat_name VARCHAR(255),
    rss_uuid UUID,
    rss_title VARCHAR(500),
    rss_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- RSS Feeds table (providers)
CREATE TABLE IF NOT EXISTS rss_feeds (
    id UUID PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    url TEXT UNIQUE NOT NULL,
    description TEXT,
    last_updated TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- RSS Articles table
CREATE TABLE IF NOT EXISTS rss_articles (
    id UUID PRIMARY KEY,
    feed_id UUID REFERENCES rss_feeds(id) ON DELETE CASCADE,
    title VARCHAR(1000) NOT NULL,
    content TEXT,
    summary TEXT,
    url TEXT,
    published_date TIMESTAMP WITH TIME ZONE,
    author VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Full-text search vector
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', title || ' ' || COALESCE(content, '') || ' ' || COALESCE(summary, ''))
    ) STORED
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_chats_updated_at ON chats(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chats_rss_uuid ON chats(rss_uuid);
CREATE INDEX IF NOT EXISTS idx_rss_feeds_url ON rss_feeds(url);
CREATE INDEX IF NOT EXISTS idx_rss_articles_feed_id ON rss_articles(feed_id);
CREATE INDEX IF NOT EXISTS idx_rss_articles_published_date ON rss_articles(published_date DESC);
CREATE INDEX IF NOT EXISTS idx_rss_articles_search ON rss_articles USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_rss_articles_created_at ON rss_articles(created_at DESC);

-- Function to update updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers
CREATE TRIGGER update_chats_updated_at 
    BEFORE UPDATE ON chats 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
