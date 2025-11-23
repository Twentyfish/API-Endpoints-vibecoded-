import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import os

# Local SQLite database
SQLITE_DB = 'blacklist.db'

# PostgreSQL connection (Railway will provide this URL)
POSTGRES_URL = os.environ.get('DATABASE_URL')

def migrate():
    # Connect to SQLite
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()
    
    # Connect to PostgreSQL
    pg_conn = psycopg2.connect(POSTGRES_URL)
    pg_cur = pg_conn.cursor()
    
    print("Creating PostgreSQL tables...")
    
    # Create tables in PostgreSQL
    pg_cur.execute('''
        CREATE TABLE IF NOT EXISTS blacklisted_users (
            user_id BIGINT PRIMARY KEY,
            username TEXT NOT NULL,
            reason TEXT,
            added_by TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    pg_cur.execute('''
        CREATE TABLE IF NOT EXISTS blacklisted_groups (
            group_id BIGINT PRIMARY KEY,
            reason TEXT,
            added_by TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    pg_cur.execute('''
        CREATE TABLE IF NOT EXISTS flagged_keywords_specific (
            id SERIAL PRIMARY KEY,
            keyword TEXT UNIQUE NOT NULL
        )
    ''')
    
    pg_cur.execute('''
        CREATE TABLE IF NOT EXISTS flagged_keywords_nonspecific (
            id SERIAL PRIMARY KEY,
            keyword TEXT UNIQUE NOT NULL
        )
    ''')
    
    pg_cur.execute('''
        CREATE TABLE IF NOT EXISTS realms_blacklist (
            user_id BIGINT PRIMARY KEY,
            username TEXT NOT NULL,
            reason TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    pg_cur.execute('''
        CREATE TABLE IF NOT EXISTS command_blacklist (
            user_id BIGINT PRIMARY KEY,
            username TEXT NOT NULL,
            reason TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    pg_conn.commit()
    print("✅ Tables created")
    
    # Migrate data from each table
    tables = [
        'blacklisted_users',
        'blacklisted_groups',
        'flagged_keywords_specific',
        'flagged_keywords_nonspecific',
        'realms_blacklist',
        'command_blacklist'
    ]
    
    for table in tables:
        print(f"\nMigrating {table}...")
        
        # Get data from SQLite
        sqlite_cur.execute(f'SELECT * FROM {table}')
        rows = sqlite_cur.fetchall()
        
        if not rows:
            print(f"  No data in {table}")
            continue
        
        # Get column names
        columns = [description[0] for description in sqlite_cur.description]
        
        # Prepare insert statement
        cols_str = ', '.join(columns)
        placeholders = ', '.join(['%s'] * len(columns))
        insert_sql = f'INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
        
        # Insert data
        data = [tuple(row) for row in rows]
        execute_values(pg_cur, insert_sql, data, template=f"({placeholders})")
        pg_conn.commit()
        
        print(f"  ✅ Migrated {len(rows)} rows")
    
    # Close connections
    sqlite_conn.close()
    pg_conn.close()
    
    print("\n✅ Migration complete!")

if __name__ == '__main__':
    if not POSTGRES_URL:
        print("❌ Error: DATABASE_URL environment variable not set")
        print("Get it from Railway dashboard → PostgreSQL → Variables → DATABASE_URL")
        exit(1)
    
    migrate()
