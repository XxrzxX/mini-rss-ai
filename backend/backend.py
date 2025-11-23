from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv
import json
import psycopg2
import os
import uuid
import time
from psycopg2.extras import RealDictCursor
from typing import List, Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError
import logging
import json

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def log_error(operation: str, error_type: str = "general", safe_details: str = None):
    """Log errors with sanitized information"""
    log_data = {
        "operation": operation,
        "error_type": error_type,
        "timestamp": datetime.now().isoformat()
    }
    if safe_details:
        log_data["details"] = safe_details
    
    logging.error(json.dumps(log_data))
from datetime import datetime
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import feedparser
from bs4 import BeautifulSoup
import urllib.parse
from urllib.request import urlopen
from urllib.request import Request as UrlRequest
from urllib.error import URLError, HTTPError

load_dotenv()

# Database Migration System
def run_migrations():
    """Run database migrations on startup"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Create migration tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Get applied migrations
            cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
            applied_versions = {row[0] for row in cursor.fetchall()}
            
            # Available migrations
            migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
            available_migrations = []
            
            if os.path.exists(migrations_dir):
                for filename in sorted(os.listdir(migrations_dir)):
                    if filename.endswith('.sql') and filename.startswith(('001', '002', '003')):
                        version = int(filename[:3])
                        available_migrations.append((version, filename))
            
            # Apply missing migrations
            for version, filename in available_migrations:
                if version not in applied_versions:
                    logging.info(f"Applying migration {version}: {filename}")
                    
                    migration_path = os.path.join(migrations_dir, filename)
                    with open(migration_path, 'r') as f:
                        migration_sql = f.read()
                    
                    # Execute migration
                    cursor.execute(migration_sql)
                    
                    # Record as applied
                    cursor.execute(
                        "INSERT INTO schema_migrations (version) VALUES (%s)",
                        (version,)
                    )
                    
                    logging.info(f"Migration {version} applied successfully")
            
            conn.commit()
            logging.info("Database migrations completed")
            
    except Exception:
        log_error("migration", "execution_failed")
        conn.rollback()
        raise
    finally:
        conn.close()

# Constants
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS").split(",") if os.environ.get("ALLOWED_ORIGINS") else []

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)

def get_secrets(secret_name=None, region_name=os.environ.get("REGION_NAME")):
    if not secret_name:
        secret_name = os.environ.get("SECRET_NAME")
    
    try:
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )
        
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code in ['ResourceNotFoundException', 'SecretNotFoundException']:
            log_error("secrets_retrieval", "not_found")
        elif error_code == 'AccessDeniedException':
            log_error("secrets_retrieval", "access_denied")
        else:
            log_error("secrets_retrieval", "aws_error")
        return {}

# Load all secrets from AWS
secrets = get_secrets()

# Access secrets as needed
DB_NAME = secrets.get(os.environ.get('DB_NAME_KEY'))
DB_USER = secrets.get(os.environ.get('DB_USER_KEY'))
DB_PASSWORD = secrets.get(os.environ.get('DB_PASSWORD_KEY'))
DB_HOST = secrets.get(os.environ.get('DB_HOST_KEY'))
DB_PORT = secrets.get(os.environ.get('DB_PORT_KEY'))
S3_BUCKET_NAME = secrets.get(os.environ.get('S3_BUCKET_KEY'))

# Strip port from DB_HOST if it contains one
if DB_HOST and ':' in DB_HOST:
    DB_HOST = DB_HOST.split(':')[0]

# Validate required secrets
if not all([DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, S3_BUCKET_NAME]):
    logging.critical("Missing required secrets. Application cannot start.")
    raise SystemExit("Critical configuration missing")

DB_CONFIG = {
    "dbname": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "host": DB_HOST,
    "port": DB_PORT,
}

# Initialize Bedrock client
try:
    bedrock_client = boto3.client('bedrock-runtime', region_name=os.environ.get("REGION_NAME"))
    logging.info("Bedrock client initialized")
except Exception:
    log_error("bedrock_init", "client_failed")
    bedrock_client = None

# Initialize S3 client
try:
    s3_client = boto3.client('s3')
    logging.info("S3 client initialized")
except Exception:
    log_error("s3_init", "client_failed")
    s3_client = None

# FastAPI app
app = FastAPI(title="RSS Chat API", version="1.0.0")

# CORS middleware (configured after ALLOWED_ORIGINS is set)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Run migrations on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup"""
    try:
        logging.info("Running database migrations...")
        run_migrations()
        logging.info("Application startup completed")
    except Exception as e:
        logging.error(f"Startup failed: {e}")
        raise

# Rate limiting
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Pydantic models
class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)

class ChatRequest(BaseModel):
    messages: List[Message]

class SaveChatRequest(BaseModel):
    chat_id: str
    messages: List[Message]
    chat_name: Optional[str] = None
    rss_uuid: Optional[str] = None
    rss_title: Optional[str] = None
    rss_url: Optional[str] = None

class LoadChatRequest(BaseModel):
    chat_id: str
    
    @validator('chat_id')
    def validate_chat_id(cls, v):
        try:
            uuid_obj = uuid.UUID(v)
            return str(uuid_obj)
        except ValueError:
            raise ValueError('Invalid UUID format')

class DeleteChatRequest(BaseModel):
    chat_id: str
    
    @validator('chat_id')
    def validate_chat_id(cls, v):
        try:
            uuid_obj = uuid.UUID(v)
            return str(uuid_obj)
        except ValueError:
            raise ValueError('Invalid UUID format')

class RSSRequest(BaseModel):
    url: str
    
    @validator('url')
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            v = 'https://' + v
        return v

class RSSChatRequest(BaseModel):
    messages: List[Message]
    rss_uuid: str
    
    @validator('rss_uuid')
    def validate_rss_uuid(cls, v):
        try:
            uuid_obj = uuid.UUID(v)
            return str(uuid_obj)
        except ValueError:
            raise ValueError('Invalid UUID format')

# Database helper functions
def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception:
        log_error("database_connection", "connection_failed")
        raise HTTPException(status_code=500, detail="Database connection failed")

def store_rss_feed_and_articles(feed_data, feed_url):
    """Store RSS feed and articles in database"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            feed_id = str(uuid.uuid4())
            
            # Insert RSS feed
            cursor.execute("""
                INSERT INTO rss_feeds (id, title, url, description, last_updated)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (url) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    last_updated = EXCLUDED.last_updated
                RETURNING id
            """, (feed_id, feed_data['title'], feed_url, feed_data['description'], datetime.now()))
            
            result = cursor.fetchone()
            feed_id = result[0] if result else feed_id
            
            # Insert articles
            for entry in feed_data['entries']:
                article_id = str(uuid.uuid4())
                published_date = None
                if entry.get('published'):
                    try:
                        import dateutil.parser
                        published_date = dateutil.parser.parse(entry['published'])
                    except:
                        pass
                
                cursor.execute("""
                    INSERT INTO rss_articles (id, feed_id, title, content, summary, url, published_date, author)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    article_id, feed_id, entry['title'], entry.get('content', ''),
                    entry['summary'], entry['link'], published_date, entry.get('author', '')
                ))
        
        conn.commit()
        return feed_id
    finally:
        conn.close()

def save_chat_to_s3(session_id: str, messages: List[Dict], context: Dict = None):
    """Save chat messages to S3"""
    if not s3_client:
        return None
    
    try:
        s3_key = f"chat-history/anonymous/{session_id}.json"
        chat_data = {
            "messages": messages,
            "context": context or {},
            "updated_at": datetime.now().isoformat()
        }
        
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=json.dumps(chat_data),
            ContentType='application/json'
        )
        return s3_key
    except Exception as e:
        log_error("s3_chat_save", "save_failed")
        return None

def load_chat_from_s3(s3_key: str):
    """Load chat messages from S3"""
    if not s3_client:
        return {"messages": [], "context": {}}
    
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        return json.loads(response['Body'].read())
    except Exception as e:
        log_error("s3_chat_load", "load_failed")
        return {"messages": [], "context": {}}

def create_chat_session(title: str = None, rss_feed_ids: List[str] = None, article_ids: List[str] = None):
    """Create new chat session in database"""
    conn = get_db_connection()
    try:
        session_id = str(uuid.uuid4())
        s3_key = f"chat-history/anonymous/{session_id}.json"
        
        # Initialize empty chat in S3
        save_chat_to_s3(session_id, [], {"rss_feed_ids": rss_feed_ids or [], "article_ids": article_ids or []})
        
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO chat_sessions (id, title, s3_key, rss_feed_ids, article_ids)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (session_id, title or "New Chat", s3_key, rss_feed_ids or [], article_ids or []))
            
            result = cursor.fetchone()
            conn.commit()
            return result[0]
    finally:
        conn.close()

def get_chat_sessions(limit: int = 20):
    """Get user's chat sessions"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, title, created_at, updated_at, rss_feed_ids, article_ids
                FROM chat_sessions 
                ORDER BY updated_at DESC 
                LIMIT %s
            """, (limit,))
            return cursor.fetchall()
    finally:
        conn.close()

def update_chat_session(session_id: str, messages: List[Dict], title: str = None):
    """Update chat session with new messages"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get current session
            cursor.execute("SELECT s3_key, rss_feed_ids, article_ids FROM chat_sessions WHERE id = %s", (session_id,))
            session = cursor.fetchone()
            
            if not session:
                raise HTTPException(status_code=404, detail="Chat session not found")
            
            # Load current context
            chat_data = load_chat_from_s3(session['s3_key'])
            context = chat_data.get('context', {})
            
            # Save updated messages to S3
            save_chat_to_s3(session_id, messages, context)
            
            # Update database
            update_fields = ["updated_at = CURRENT_TIMESTAMP"]
            params = []
            
            if title:
                update_fields.append("title = %s")
                params.append(title)
            
            params.append(session_id)
            
            cursor.execute(f"""
                UPDATE chat_sessions 
                SET {', '.join(update_fields)}
                WHERE id = %s
            """, params)
            
            conn.commit()
            return session_id
    finally:
        conn.close()
    """Get RSS context using Option 3: Recent articles + keyword search"""
    
    conn = get_db_connection()
    if not conn:
        return ""
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get recent articles (last 48 hours)
            cursor.execute("""
                SELECT a.title, a.summary, a.content, f.title as feed_title
                FROM rss_articles a
                JOIN rss_feeds f ON a.feed_id = f.id
                WHERE a.created_at >= NOW() - INTERVAL '48 hours'
                ORDER BY a.created_at DESC
                LIMIT 15
            """)
            recent_articles = cursor.fetchall()
            
            # Get keyword-matched older articles if user query provided
            older_articles = []
            if user_query.strip():
                cursor.execute("""
                    SELECT a.title, a.summary, a.content, f.title as feed_title
                    FROM rss_articles a
                    JOIN rss_feeds f ON a.feed_id = f.id
                    WHERE a.created_at < NOW() - INTERVAL '48 hours'
                    AND a.search_vector @@ plainto_tsquery('english', %s)
                    ORDER BY ts_rank(a.search_vector, plainto_tsquery('english', %s)) DESC
                    LIMIT 15
                """, (user_query, user_query))
                older_articles = cursor.fetchall()
            
            # Build context
            context = "RSS Feed Articles:\n\n"
            
            if recent_articles:
                context += "=== RECENT ARTICLES (Last 48 hours) ===\n"
                for article in recent_articles:
                    context += f"Feed: {article['feed_title']}\n"
                    context += f"Title: {article['title']}\n"
                    context += f"Summary: {article['summary'][:300]}...\n\n"
            
            if older_articles:
                context += "=== RELEVANT OLDER ARTICLES ===\n"
                for article in older_articles:
                    context += f"Feed: {article['feed_title']}\n"
                    context += f"Title: {article['title']}\n"
                    context += f"Summary: {article['summary'][:300]}...\n\n"
            
            return context[:8000]  # Limit context size
    finally:
        conn.close()
    if not s3_client:
        return {"status": "skipped", "reason": "s3_unavailable"}
    
    try:
        return operation(**kwargs)
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            raise HTTPException(status_code=404, detail="S3 bucket not found")
        elif error_code == 'NoSuchKey':
            raise HTTPException(status_code=404, detail="Resource not found in S3")
        else:
            raise HTTPException(status_code=500, detail="S3 operation failed")

# RSS Helper Functions
def discover_rss_feeds(url):
    """Automatically discover RSS feeds from a website."""
    feeds = []
    try:
        req = UrlRequest(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=15) as response:  # Increased timeout slightly
            content = response.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(content, 'html.parser')
            
        # Look for RSS/Atom links
        for link in soup.find_all('link', type=['application/rss+xml', 'application/atom+xml']):
            feed_url = urllib.parse.urljoin(url, link.get('href', ''))
            feeds.append({'url': feed_url, 'title': link.get('title', 'RSS Feed')})
            
        # Common RSS paths (reduced for speed)
        if not feeds:  # Only try common paths if no feeds found
            common_paths = ['/rss', '/feed', '/rss.xml']  # Reduced list
            for path in common_paths:
                test_url = urllib.parse.urljoin(url, path)
                try:
                    req = UrlRequest(test_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urlopen(req, timeout=5) as test_response:
                        if test_response.status == 200:
                            feeds.append({'url': test_url, 'title': f'RSS Feed ({path})'})
                            break  # Stop after finding first working feed
                except:
                    continue
                
    except Exception as e:
        logging.error(f"RSS discovery error: {str(e)}")
        
    return feeds[:5]  # Limit to 5 feeds max

def parse_rss_feed(url):
    """Parse RSS feed and return structured data."""
    try:
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            raise ValueError("Invalid RSS feed")
            
        feed_data = {
            'title': feed.feed.get('title', 'Unknown Feed'),
            'description': feed.feed.get('description', ''),
            'link': feed.feed.get('link', ''),
            'entries': []
        }
        
        for entry in feed.entries[:20]:  # Limit to 20 entries
            feed_data['entries'].append({
                'title': entry.get('title', 'No Title'),
                'link': entry.get('link', ''),
                'summary': entry.get('summary', entry.get('description', '')),
                'published': entry.get('published', ''),
                'author': entry.get('author', '')
            })
            
        return feed_data
    except Exception as e:
        logging.error(f"RSS parsing error: {str(e)}")
        raise ValueError(f"Failed to parse RSS feed: {str(e)}")

# Bedrock Nova Lite helper function
def call_bedrock_nova(messages, system_prompt=None):
    """Call AWS Bedrock Nova Lite model with improved settings."""
    if not bedrock_client:
        return os.environ.get("BEDROCK_MOCK_RESPONSE")
    
    try:
        # Improved system prompt for news articles
        if not system_prompt:
            system_prompt = (
                "You are a helpful AI assistant. Provide direct, concise answers. "
                "Do not repeat the user's question. Do not start with phrases like "
                "'Based on your question' or 'You asked about'. "
                "Answer directly and briefly in 1-2 sentences maximum."
            )
        
        # Prepare messages for Nova Lite - limit context to prevent loops
        conversation = []
        if system_prompt:
            conversation.append({
                "role": "user",
                "content": [{"text": system_prompt}]
            })
            conversation.append({
                "role": "assistant", 
                "content": [{"text": "Understood. I'll provide direct, concise answers."}]
            })
        
        # Only use the last 3 messages to prevent context overflow
        recent_messages = messages[-3:] if len(messages) > 3 else messages
        for msg in recent_messages:
            # Handle both dict and object formats
            role = msg.role if hasattr(msg, 'role') else msg['role']
            content = msg.content if hasattr(msg, 'content') else msg['content']
            conversation.append({
                "role": role,
                "content": [{"text": content}]
            })
        
        response = bedrock_client.converse(
            modelId=os.environ.get("BEDROCK_MODEL_ID"),
            messages=conversation,
            inferenceConfig={
                "maxTokens": 500,  # Increased for complete responses
                "temperature": 0.3,
                "topP": 0.8,
                "stopSequences": ["Human:", "User:"]
            }
        )
        
        response_text = response['output']['message']['content'][0]['text']
        return response_text.strip()
        
    except Exception as e:
        logging.error(f"Bedrock error: {str(e)}")
        raise HTTPException(status_code=500, detail="AI service unavailable")

# API Endpoints
@app.post("/chat/", response_model=None)
async def chat(request: Request, chat_req: ChatRequest):
    try:
        # Return JSON payload for consistency with other endpoints
        response_text = call_bedrock_nova(chat_req.messages)
        return {"response": response_text}
    except Exception as e:
        logging.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process chat request")

@app.post("/save_chat/")
@limiter.limit("10/minute")
async def save_chat(request: Request, save_req: SaveChatRequest):
    try:
        conn = get_db_connection()
        if not conn:
            return {"message": "Database unavailable"}
            
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO chats (id, messages, chat_name, rss_uuid, rss_title, rss_url, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    messages = EXCLUDED.messages,
                    chat_name = EXCLUDED.chat_name,
                    rss_uuid = EXCLUDED.rss_uuid,
                    rss_title = EXCLUDED.rss_title,
                    rss_url = EXCLUDED.rss_url,
                    updated_at = EXCLUDED.updated_at
            """, (
                save_req.chat_id,
                json.dumps([msg.dict() for msg in save_req.messages]),
                save_req.chat_name,
                save_req.rss_uuid,
                save_req.rss_title,
                save_req.rss_url,
                datetime.now(),
                datetime.now()
            ))
        conn.commit()
        conn.close()
        
        return {"message": "Chat saved successfully"}
    except Exception as e:
        logging.error(f"Save chat error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save chat")

@app.post("/load_chat/")
@limiter.limit("30/minute")
async def load_chat(request: Request, load_req: LoadChatRequest):
    try:
        conn = get_db_connection()
        if not conn:
            return {"chats": []}
            
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            if load_req.chat_id == "all":
                cursor.execute("SELECT * FROM chats ORDER BY updated_at DESC")
                chats = cursor.fetchall()
            else:
                cursor.execute("SELECT * FROM chats WHERE id = %s", (load_req.chat_id,))
                chats = cursor.fetchall()
        
        conn.close()
        
        for chat in chats:
            if chat['messages']:
                chat['messages'] = json.loads(chat['messages'])
        
        return {"chats": chats}
    except Exception as e:
        logging.error(f"Load chat error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to load chat")

@app.post("/delete_chat/")
@limiter.limit("10/minute")
async def delete_chat(request: Request, delete_req: DeleteChatRequest):
    try:
        conn = get_db_connection()
        if not conn:
            return {"message": "Database unavailable"}
            
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM chats WHERE id = %s", (delete_req.chat_id,))
        conn.commit()
        conn.close()
        
        return {"message": "Chat deleted successfully"}
    except Exception as e:
        logging.error(f"Delete chat error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete chat")

@app.post("/discover_rss/")
@limiter.limit("10/minute")
async def discover_rss(
    request: Request,
    rss_req: RSSRequest
):
    try:
        feeds = discover_rss_feeds(rss_req.url)
        return {"feeds": feeds, "source_url": rss_req.url}
    except Exception as e:
        logging.error(f"RSS discovery error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to discover RSS feeds")

@app.post("/add_rss/")
async def add_rss(
    request: Request,
    rss_req: RSSRequest
):
    try:
        # Parse RSS feed
        feed_data = parse_rss_feed(rss_req.url)
        
        # Store in database
        feed_id = store_rss_feed_and_articles(feed_data, rss_req.url)
        
        return {
            "message": "RSS feed added successfully",
            "rss_uuid": feed_id,
            "feed_title": feed_data['title'],
            "entries_count": len(feed_data['entries'])
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"RSS add error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to add RSS feed")

@app.post("/rss_chat/", response_model=None)
@limiter.limit("20/minute")
async def rss_chat(
    request: Request,
    rss_req: RSSChatRequest
):
    try:
        # Get user input for keyword search
        user_input = rss_req.messages[-1].content if rss_req.messages[-1].role == "user" else ""
        if not user_input:
            raise HTTPException(status_code=400, detail="Last message must be from user")

        # Get RSS context using Option 3 strategy
        rss_context = get_rss_context_for_ai(user_input)
        
        # Create system prompt with RSS context
        system_prompt = (
            "You are a helpful news assistant discussing publicly available RSS feed content. "
            "The articles below are from public RSS feeds and news sources. "
            "You should freely discuss, analyze, and provide insights about these public news articles. "
            "These are not confidential - they are published news stories meant to be shared and discussed. "
            "Provide helpful summaries, analysis, and insights based on the feed content. "
            "If you don't have specific information about something, say so.\n\n"
            f"RSS ARTICLES:\n{rss_context}"
        )

        # Call Bedrock with RSS context
        response_text = call_bedrock_nova(rss_req.messages, system_prompt)
        
        # Return complete response instead of streaming to avoid loops
        return {"response": response_text}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"RSS chat error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process RSS chat request")

@app.get("/articles")
@limiter.limit("30/minute")
async def get_all_articles(request: Request, limit: int = 50):
    """Get all articles across all feeds"""
    try:
        conn = get_db_connection()
        if not conn:
            return {"articles": []}
            
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT a.id, a.title, a.summary, a.url, a.published_date, a.author,
                       f.title as feed_title, f.id as feed_id
                FROM rss_articles a
                JOIN rss_feeds f ON a.feed_id = f.id
                ORDER BY a.created_at DESC 
                LIMIT %s
            """, (limit,))
            articles = cursor.fetchall()
        
        conn.close()
        
        # Convert to list of dicts
        article_list = []
        for article in articles:
            article_list.append({
                "id": str(article['id']),
                "title": article['title'],
                "summary": article['summary'] or "",
                "url": article['url'] or "",
                "published_date": str(article['published_date']) if article['published_date'] else "",
                "author": article['author'] or "",
                "feed_title": article['feed_title'],
                "feed_id": str(article['feed_id'])
            })
        
        return {"articles": article_list}
        
    except Exception as e:
        logging.error(f"Get all articles error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get articles")

@app.get("/search_articles")
async def search_articles(q: str, limit: int = 10):
    """Search articles using full-text search"""
    if not q.strip():
        return {"articles": []}
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT a.id, a.title, a.summary, a.url, a.published_date, 
                       f.title as feed_title, f.id as feed_id,
                       ts_rank(a.search_vector, to_tsquery('english', %s)) as rank
                FROM rss_articles a
                JOIN rss_feeds f ON a.feed_id = f.id
                WHERE a.search_vector @@ to_tsquery('english', %s)
                ORDER BY rank DESC, a.published_date DESC
                LIMIT %s
            """, (q, q, limit))
            
            articles = []
            for row in cursor.fetchall():
                articles.append({
                    "id": str(row['id']),
                    "title": row['title'],
                    "summary": row['summary'][:200] + "..." if row['summary'] and len(row['summary']) > 200 else row['summary'],
                    "url": row['url'],
                    "published_date": row['published_date'].isoformat() if row['published_date'] else None,
                    "feed_title": row['feed_title'],
                    "feed_id": str(row['feed_id']),
                    "relevance": float(row['rank'])
                })
            
            return {"articles": articles}
    finally:
        conn.close()

@app.post("/chat_article")
async def chat_article(request: Request, article_req: dict):
    """Chat about a specific article"""
    article_id = article_req.get("article_id")
    message = article_req.get("message", "Tell me about this article")
    
    if not article_id:
        raise HTTPException(status_code=400, detail="Article ID required")
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT a.title, a.content, a.summary, a.url, f.title as feed_title
                FROM rss_articles a
                JOIN rss_feeds f ON a.feed_id = f.id
                WHERE a.id = %s
            """, (article_id,))
            
            article = cursor.fetchone()
            if not article:
                raise HTTPException(status_code=404, detail="Article not found")
            
            # Create focused context with just this article
            article_context = f"""
Article: {article['title']}
Source: {article['feed_title']}
Summary: {article['summary'] or 'No summary available'}
URL: {article['url']}
"""
            
            system_prompt = f"""You are discussing this specific news article:
{article_context}

Answer questions about this article directly and concisely. If asked for details not in the article, say so."""
            
            messages = [{"role": "user", "content": message}]
            response_text = call_bedrock_nova(messages, system_prompt)
            
            return {"response": response_text, "article": {
                "title": article['title'],
                "url": article['url'],
                "feed_title": article['feed_title']
            }}
    finally:
        conn.close()

@app.get("/rss_articles/{feed_id}")
async def get_rss_articles(request: Request, feed_id: str):
    try:
        conn = get_db_connection()
        if not conn:
            return {"articles": []}
            
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT title, summary, url, published_date, author
                FROM rss_articles 
                WHERE feed_id = %s 
                ORDER BY published_date DESC 
                LIMIT 20
            """, (feed_id,))
            articles = cursor.fetchall()
        
        conn.close()
        
        # Convert to list of dicts
        article_list = []
        for article in articles:
            article_list.append({
                "title": article['title'],
                "summary": article['summary'] or "",
                "url": article['url'] or "",
                "published_date": str(article['published_date']) if article['published_date'] else "",
                "author": article['author'] or ""
            })
        
        return {"articles": article_list}
        
    except Exception as e:
        logging.error(f"Get articles error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get articles")

# Chat Session Models
class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Chat"
    rss_feed_ids: Optional[List[str]] = []
    article_ids: Optional[List[str]] = []

class ChatRequest(BaseModel):
    session_id: str
    message: str

# Chat Session Management Functions
def save_chat_to_s3(session_id: str, messages: List[Dict], context: Dict = None):
    """Save chat messages to S3"""
    if not s3_client:
        return None
    
    try:
        s3_key = f"chat-history/anonymous/{session_id}.json"
        chat_data = {
            "messages": messages,
            "context": context or {},
            "updated_at": datetime.now().isoformat()
        }
        
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=json.dumps(chat_data),
            ContentType='application/json'
        )
        return s3_key
    except Exception as e:
        log_error("s3_chat_save", "save_failed")
        return None

def load_chat_from_s3(s3_key: str):
    """Load chat messages from S3"""
    if not s3_client:
        return {"messages": [], "context": {}}
    
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        return json.loads(response['Body'].read())
    except Exception as e:
        log_error("s3_chat_load", "load_failed")
        return {"messages": [], "context": {}}

def create_chat_session(title: str = None, rss_feed_ids: List[str] = None, article_ids: List[str] = None):
    """Create new chat session in database"""
    conn = get_db_connection()
    try:
        session_id = str(uuid.uuid4())
        s3_key = f"chat-history/anonymous/{session_id}.json"
        
        # Initialize empty chat in S3
        save_chat_to_s3(session_id, [], {"rss_feed_ids": rss_feed_ids or [], "article_ids": article_ids or []})
        
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO chat_sessions (id, title, s3_key, rss_feed_ids, article_ids)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (session_id, title or "New Chat", s3_key, rss_feed_ids or [], article_ids or []))
            
            result = cursor.fetchone()
            conn.commit()
            return result[0]
    finally:
        conn.close()

def get_articles_context(article_ids: List[str]) -> str:
    """Get context from specific articles"""
    if not article_ids:
        return ""
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Convert string IDs to UUID format for database query
            uuid_params = []
            for article_id in article_ids:
                try:
                    # Try to convert string to UUID format
                    import uuid
                    uuid.UUID(article_id)  # Validate UUID format
                    uuid_params.append(article_id)
                except ValueError:
                    # Skip invalid UUIDs
                    logging.warning(f"Invalid UUID format: {article_id}")
                    continue
            
            if not uuid_params:
                return "No valid article IDs provided."
            
            placeholders = ','.join(['%s'] * len(uuid_params))
            cursor.execute(f"""
                SELECT a.title, a.summary, a.content, f.title as feed_title
                FROM rss_articles a
                JOIN rss_feeds f ON a.feed_id = f.id
                WHERE a.id::text IN ({placeholders})
                LIMIT 10
            """, uuid_params)
            
            articles = cursor.fetchall()
            
            if not articles:
                return "No articles found for the provided IDs."
            
            context = "Selected Articles:\n\n"
            for article in articles:
                context += f"Feed: {article['feed_title']}\n"
                context += f"Title: {article['title']}\n"
                context += f"Summary: {article['summary'][:300]}...\n\n"
            
            return context[:8000]  # Limit context size
    finally:
        conn.close()

# Chat Session API Endpoints
@app.post("/chat_sessions/")
@limiter.limit("10/minute")
async def create_new_chat_session(request: Request, chat_data: ChatSessionCreate):
    """Create a new chat session"""
    try:
        session_id = create_chat_session(
            title=chat_data.title,
            rss_feed_ids=chat_data.rss_feed_ids,
            article_ids=chat_data.article_ids
        )
        return {"session_id": session_id, "message": "Chat session created"}
    except Exception as e:
        log_error("chat_session_create", "creation_failed")
        raise HTTPException(status_code=500, detail="Failed to create chat session")

@app.get("/chat_sessions/")
@limiter.limit("30/minute")
async def list_chat_sessions(request: Request):
    """List user's chat sessions"""
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, title, created_at, updated_at, rss_feed_ids, article_ids
                FROM chat_sessions 
                ORDER BY updated_at DESC 
                LIMIT 20
            """)
            sessions = cursor.fetchall()
            return {"sessions": sessions}
    except Exception as e:
        log_error("chat_sessions_list", "list_failed")
        raise HTTPException(status_code=500, detail="Failed to list chat sessions")
    finally:
        conn.close()

@app.post("/chat_sessions/{session_id}/chat")
@limiter.limit("20/minute")
async def chat_with_session(request: Request, session_id: str, chat_req: ChatRequest):
    """Chat within a specific session"""
    try:
        # Get session
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT s3_key, rss_feed_ids, article_ids 
                FROM chat_sessions WHERE id = %s
            """, (session_id,))
            session = cursor.fetchone()
            
            if not session:
                raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Load current messages
        chat_data = load_chat_from_s3(session['s3_key'])
        messages = chat_data.get('messages', [])
        
        # Add user message
        messages.append({"role": "user", "content": chat_req.message})
        
        # Get AI response with context
        rss_context = ""
        if session['article_ids']:
            rss_context = get_articles_context(session['article_ids'])
        elif session['rss_feed_ids']:
            rss_context = get_rss_context_for_ai(chat_req.message)
        
        # Call AI
        ai_response = call_bedrock_nova([{"role": "user", "content": chat_req.message}], 
                                       system_prompt=f"RSS Context:\n{rss_context}")
        
        # Add AI response
        messages.append({"role": "assistant", "content": ai_response})
        
        # Save updated messages
        save_chat_to_s3(session_id, messages, {"rss_feed_ids": session['rss_feed_ids'], "article_ids": session['article_ids']})
        
        # Update session timestamp
        with conn.cursor() as cursor:
            cursor.execute("UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = %s", (session_id,))
            conn.commit()
        
        return {"response": ai_response}
        
    except HTTPException:
        raise
    except Exception as e:
        log_error("chat_session_chat", "chat_failed")
        raise HTTPException(status_code=500, detail="Failed to process chat")
    finally:
        conn.close()

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/rss_feeds")
async def get_rss_feeds():
    """Get all stored RSS feeds"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM rss_feeds ORDER BY created_at DESC")
            feeds = cursor.fetchall()
            return {"feeds": feeds}
    except Exception as e:
        logging.error(f"Failed to get RSS feeds: {e}")
        raise HTTPException(status_code=500, detail="Failed to get RSS feeds")
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.environ.get("HOST"), port=int(os.environ.get("PORT")))
