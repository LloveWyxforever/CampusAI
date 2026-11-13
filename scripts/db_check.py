from app.store import init, connection

init()
with connection() as c:
    print('SQLite integrity:',c.execute('PRAGMA integrity_check').fetchone()[0])
