import os
import re
import sqlite3
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = Path(os.environ.get('CAMPUSAI_DB', ROOT / 'data/campusai.db'))


def connection():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=20)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c


def init():
    with connection() as c:
        c.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS chats(id TEXT PRIMARY KEY,title TEXT NOT NULL,campus TEXT NOT NULL,created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,chat_id TEXT REFERENCES chats(id) ON DELETE CASCADE,role TEXT,content TEXT,sources TEXT DEFAULT '[]',status TEXT DEFAULT 'complete',created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,name TEXT,category TEXT,campus TEXT,source TEXT,status TEXT,error TEXT,stored TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY,document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,content TEXT);
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(content, tokenize='trigram');
        CREATE TRIGGER IF NOT EXISTS chunk_delete AFTER DELETE ON chunks BEGIN DELETE FROM chunks_fts WHERE rowid=old.id; END;
        ''')


def uid():
    return uuid.uuid4().hex


def search(query, campus='未选择', limit=5):
    # FTS5 trigram works for Chinese; overlapping triples avoid requiring spaces.
    runs = re.findall(r'[\u4e00-\u9fff]{3,}|[A-Za-z0-9]{3,}', query[:500])
    tokens = list(dict.fromkeys(t[i:i+3] for t in runs for i in range(len(t)-2)))[:80]
    with connection() as c:
        if tokens:
            match = ' OR '.join('"' + t + '"' for t in tokens)
            rows = c.execute('''SELECT k.content,d.id,d.name,d.source,d.campus,bm25(chunks_fts) score
                FROM chunks_fts JOIN chunks k ON k.id=chunks_fts.rowid JOIN documents d ON d.id=k.document_id
                WHERE chunks_fts MATCH ? AND d.status='ready' AND (d.campus='通用' OR d.campus=? OR ?='未选择')
                ORDER BY score LIMIT ?''', (match,campus,campus,limit)).fetchall()
            if rows:
                return [dict(r) for r in rows]
        words = re.findall(r'[\u4e00-\u9fff]{2}|[a-zA-Z]{2,}',query[:200])[:40]
        if not words:
            return []
        condition = ' OR '.join('k.content LIKE ?' for _ in words)
        rows = c.execute(f'''SELECT k.content,d.id,d.name,d.source,d.campus FROM chunks k JOIN documents d ON d.id=k.document_id
            WHERE d.status='ready' AND (d.campus='通用' OR d.campus=? OR ?='未选择') AND ({condition}) LIMIT ?''',
            (campus,campus,*['%'+w+'%' for w in words],limit)).fetchall()
        return [dict(r) for r in rows]
