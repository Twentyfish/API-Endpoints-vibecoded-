from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from datetime import datetime
from functools import wraps

# Test
# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
CORS(app)

# PostgreSQL connection pool
DATABASE_URL = os.environ.get('DATABASE_URL', "postgresql://postgres:UMlftzQXuwyQVSMqEMMiNXBXjdhwYxwj@postgres.railway.internal:5432/railway")

if not DATABASE_URL:
    print("\n" + "="*60)
    print("⚠️  WARNING: DATABASE_URL environment variable is not set!")
    print("="*60)
    print("Please set it using one of these methods:")
    print("\n1. Create a .env file with:")
    print("   DATABASE_URL=postgresql://user:pass@host:port/database")
    print("\n2. Set environment variable:")
    print("   Windows: set DATABASE_URL=postgresql://user:pass@host:port/db")
    print("   Linux/Mac: export DATABASE_URL=postgresql://user:pass@host:port/db")
    print("\n3. Pass it when running:")
    print("   DATABASE_URL=postgresql://... python app.py")
    print("="*60 + "\n")

# Initialize connection pool
connection_pool = None
if DATABASE_URL:
    try:
        connection_pool = ConnectionPool(
            DATABASE_URL,
            min_size=1,
            max_size=20
        )
        if connection_pool:
            print("✓ Connection pool created successfully")
            # Test the connection
            with connection_pool.connection() as test_conn:
                with test_conn.cursor() as test_cur:
                    test_cur.execute('SELECT version()')
                    version = test_cur.fetchone()[0]
                    print(f"✓ Connected to PostgreSQL")
                    print(f"  {version[:80]}...")
    except Exception as e:
        print(f"✗ Error creating connection pool: {e}")
        print("  The application will start but database operations will fail.")
        connection_pool = None
else:
    print("✗ DATABASE_URL not configured. Database features will not work.")

def get_db_connection():
    """Get a connection from the pool"""
    if not connection_pool:
        raise Exception("Database connection pool not initialized. Please set DATABASE_URL.")
    return connection_pool.connection()

def return_db_connection(conn):
    """Return a connection to the pool"""
    conn.close()

def handle_db_errors(f):
    """Decorator for handling database errors"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as db_err:
            if "not initialized" in str(db_err):
                return jsonify({
                    'error': 'Database not configured',
                    'message': 'Please set DATABASE_URL environment variable'
                }), 503
            return jsonify({
                'error': 'Database error occurred',
                'details': str(db_err)
            }), 500
    return decorated_function

# ==================== BLACKLISTED USERS ====================

@app.route('/api/blacklisted-users', methods=['GET'])
@handle_db_errors
def get_blacklisted_users():
    """Get all blacklisted users"""
    conn = get_db_connection()
    cur = conn.cursor(row_factory=dict_row)
    try:
        cur.execute('SELECT * FROM blacklisted_users ORDER BY added_at DESC')
        users = cur.fetchall()
        return jsonify([dict(user) for user in users])
    finally:
        cur.close()
        return_db_connection(conn)

@app.route('/api/blacklisted-users/<int:user_id>', methods=['GET'])
@handle_db_errors
def get_blacklisted_user(user_id):
    """Get specific blacklisted user by ID"""
    conn = get_db_connection()
    cur = conn.cursor(row_factory=dict_row)
    try:
        cur.execute('SELECT * FROM blacklisted_users WHERE user_id = %s', (user_id,))
        user = cur.fetchone()
        
        if user is None:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify(dict(user))
    finally:
        cur.close()
        return_db_connection(conn)

@app.route('/api/blacklisted-users', methods=['POST'])
@handle_db_errors
def add_blacklisted_user():
    """Add a new blacklisted user"""
    data = request.get_json()
    
    user_id = data.get('user_id')
    username = data.get('username')
    reason = data.get('reason')
    added_by = data.get('added_by')
    
    if not all([user_id, username, reason, added_by]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            'INSERT INTO blacklisted_users (user_id, username, reason, added_by) VALUES (%s, %s, %s, %s)',
            (user_id, username, reason, added_by)
        )
        conn.commit()
        return jsonify({'message': 'User added to blacklist', 'user_id': user_id}), 201
    except psycopg.IntegrityError:
        conn.rollback()
        return jsonify({'error': 'User already exists in blacklist'}), 409
    finally:
        cur.close()
        return_db_connection(conn)

@app.route('/api/blacklisted-users/<int:user_id>', methods=['DELETE'])
@handle_db_errors
def remove_blacklisted_user(user_id):
    """Remove a user from blacklist"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM blacklisted_users WHERE user_id = %s', (user_id,))
        rowcount = cur.rowcount
        conn.commit()
        
        if rowcount == 0:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'message': 'User removed from blacklist'})
    finally:
        cur.close()
        return_db_connection(conn)

# ==================== BLACKLISTED GROUPS ====================

@app.route('/api/blacklisted-groups', methods=['GET'])
@handle_db_errors
def get_blacklisted_groups():
    """Get all blacklisted groups"""
    conn = get_db_connection()
    cur = conn.cursor(row_factory=dict_row)
    try:
        cur.execute('SELECT * FROM blacklisted_groups ORDER BY added_at DESC')
        groups = cur.fetchall()
        return jsonify([dict(group) for group in groups])
    finally:
        cur.close()
        return_db_connection(conn)

@app.route('/api/blacklisted-groups/<int:group_id>', methods=['GET'])
@handle_db_errors
def get_blacklisted_group(group_id):
    """Get specific blacklisted group by ID"""
    conn = get_db_connection()
    cur = conn.cursor(row_factory=dict_row)
    try:
        cur.execute('SELECT * FROM blacklisted_groups WHERE group_id = %s', (group_id,))
        group = cur.fetchone()
        
        if group is None:
            return jsonify({'error': 'Group not found'}), 404
        
        return jsonify(dict(group))
    finally:
        cur.close()
        return_db_connection(conn)

@app.route('/api/blacklisted-groups', methods=['POST'])
@handle_db_errors
def add_blacklisted_group():
    """Add a new blacklisted group"""
    data = request.get_json()
    
    group_id = data.get('group_id')
    reason = data.get('reason')
    added_by = data.get('added_by')
    
    if not all([group_id, reason, added_by]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            'INSERT INTO blacklisted_groups (group_id, reason, added_by) VALUES (%s, %s, %s)',
            (group_id, reason, added_by)
        )
        conn.commit()
        return jsonify({'message': 'Group added to blacklist', 'group_id': group_id}), 201
    except psycopg.IntegrityError:
        conn.rollback()
        return jsonify({'error': 'Group already exists in blacklist'}), 409
    finally:
        cur.close()
        return_db_connection(conn)

@app.route('/api/blacklisted-groups/<int:group_id>', methods=['DELETE'])
@handle_db_errors
def remove_blacklisted_group(group_id):
    """Remove a group from blacklist"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM blacklisted_groups WHERE group_id = %s', (group_id,))
        rowcount = cur.rowcount
        conn.commit()
        
        if rowcount == 0:
            return jsonify({'error': 'Group not found'}), 404
        
        return jsonify({'message': 'Group removed from blacklist'})
    finally:
        cur.close()
        return_db_connection(conn)

# ==================== FLAGGED KEYWORDS ====================

@app.route('/api/keywords/specific', methods=['GET'])
@handle_db_errors
def get_specific_keywords():
    """Get all specific flagged keywords"""
    conn = get_db_connection()
    cur = conn.cursor(row_factory=dict_row)
    try:
        cur.execute('SELECT * FROM flagged_keywords_specific ORDER BY keyword')
        keywords = cur.fetchall()
        return jsonify([dict(kw) for kw in keywords])
    finally:
        cur.close()
        return_db_connection(conn)

@app.route('/api/keywords/nonspecific', methods=['GET'])
@handle_db_errors
def get_nonspecific_keywords():
    """Get all nonspecific flagged keywords"""
    conn = get_db_connection()
    cur = conn.cursor(row_factory=dict_row)
    try:
        cur.execute('SELECT * FROM flagged_keywords_nonspecific ORDER BY keyword')
        keywords = cur.fetchall()
        return jsonify([dict(kw) for kw in keywords])
    finally:
        cur.close()
        return_db_connection(conn)

@app.route('/api/keywords/all', methods=['GET'])
@handle_db_errors
def get_all_keywords():
    """Get all flagged keywords from both tables"""
    conn = get_db_connection()
    cur = conn.cursor(row_factory=dict_row)
    try:
        cur.execute('SELECT *, \'specific\' as type FROM flagged_keywords_specific')
        specific = cur.fetchall()
        cur.execute('SELECT *, \'nonspecific\' as type FROM flagged_keywords_nonspecific')
        nonspecific = cur.fetchall()
        
        all_keywords = [dict(kw) for kw in specific] + [dict(kw) for kw in nonspecific]
        return jsonify(all_keywords)
    finally:
        cur.close()
        return_db_connection(conn)

@app.route('/api/keywords/check', methods=['POST'])
@handle_db_errors
def check_text_for_keywords():
    """Check if text contains any flagged keywords"""
    data = request.get_json()
    text = data.get('text', '').lower()
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    conn = get_db_connection()
    cur = conn.cursor(row_factory=dict_row)
    try:
        cur.execute('SELECT keyword FROM flagged_keywords_specific')
        specific = cur.fetchall()
        cur.execute('SELECT keyword FROM flagged_keywords_nonspecific')
        nonspecific = cur.fetchall()
        
        found_keywords = []
        
        # Check specific keywords (exact match)
        for row in specific:
            keyword = row['keyword'].lower()
            if keyword in text:
                found_keywords.append({'keyword': row['keyword'], 'type': 'specific'})
        
        # Check nonspecific keywords (partial match)
        for row in nonspecific:
            keyword = row['keyword'].lower()
            if keyword in text:
                found_keywords.append({'keyword': row['keyword'], 'type': 'nonspecific'})
        
        return jsonify({
            'flagged': len(found_keywords) > 0,
            'keywords_found': found_keywords,
            'count': len(found_keywords)
        })
    finally:
        cur.close()
        return_db_connection(conn)

# ==================== REALMS & COMMAND BLACKLIST ====================

@app.route('/api/realms-blacklist', methods=['GET'])
@handle_db_errors
def get_realms_blacklist():
    """Get all users on realms blacklist"""
    conn = get_db_connection()
    cur = conn.cursor(row_factory=dict_row)
    try:
        cur.execute('SELECT * FROM realms_blacklist ORDER BY added_at DESC')
        users = cur.fetchall()
        return jsonify([dict(user) for user in users])
    finally:
        cur.close()
        return_db_connection(conn)

@app.route('/api/command-blacklist', methods=['GET'])
@handle_db_errors
def get_command_blacklist():
    """Get all users on command blacklist"""
    conn = get_db_connection()
    cur = conn.cursor(row_factory=dict_row)
    try:
        cur.execute('SELECT * FROM command_blacklist ORDER BY added_at DESC')
        users = cur.fetchall()
        return jsonify([dict(user) for user in users])
    finally:
        cur.close()
        return_db_connection(conn)

# ==================== SEARCH & UTILITY ====================

@app.route('/api/search/user/<username>', methods=['GET'])
@handle_db_errors
def search_user(username):
    """Search for a user across all blacklist tables"""
    conn = get_db_connection()
    cur = conn.cursor(row_factory=dict_row)
    
    try:
        results = {
            'blacklisted_users': [],
            'realms_blacklist': [],
            'command_blacklist': []
        }
        
        # Search in blacklisted_users
        cur.execute(
            'SELECT * FROM blacklisted_users WHERE username ILIKE %s',
            (f'%{username}%',)
        )
        results['blacklisted_users'] = [dict(u) for u in cur.fetchall()]
        
        # Search in realms_blacklist
        cur.execute(
            'SELECT * FROM realms_blacklist WHERE username ILIKE %s',
            (f'%{username}%',)
        )
        results['realms_blacklist'] = [dict(r) for r in cur.fetchall()]
        
        # Search in command_blacklist
        cur.execute(
            'SELECT * FROM command_blacklist WHERE username ILIKE %s',
            (f'%{username}%',)
        )
        results['command_blacklist'] = [dict(c) for c in cur.fetchall()]
        
        return jsonify(results)
    finally:
        cur.close()
        return_db_connection(conn)

@app.route('/api/stats', methods=['GET'])
@handle_db_errors
def get_stats():
    """Get statistics about the database"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        stats = {}
        
        cur.execute('SELECT COUNT(*) FROM blacklisted_users')
        stats['blacklisted_users'] = cur.fetchone()[0]
        
        cur.execute('SELECT COUNT(*) FROM blacklisted_groups')
        stats['blacklisted_groups'] = cur.fetchone()[0]
        
        cur.execute('SELECT COUNT(*) FROM flagged_keywords_specific')
        stats['flagged_keywords_specific'] = cur.fetchone()[0]
        
        cur.execute('SELECT COUNT(*) FROM flagged_keywords_nonspecific')
        stats['flagged_keywords_nonspecific'] = cur.fetchone()[0]
        
        cur.execute('SELECT COUNT(*) FROM realms_blacklist')
        stats['realms_blacklist'] = cur.fetchone()[0]
        
        cur.execute('SELECT COUNT(*) FROM command_blacklist')
        stats['command_blacklist'] = cur.fetchone()[0]
        
        return jsonify(stats)
    finally:
        cur.close()
        return_db_connection(conn)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    if not connection_pool:
        return jsonify({
            'status': 'unhealthy',
            'database': 'not configured',
            'message': 'DATABASE_URL not set'
        }), 503
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('SELECT 1')
        return_db_connection(conn)
        return jsonify({
            'status': 'healthy',
            'database': 'connected'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'error',
            'error': str(e)
        }), 503

@app.route('/', methods=['GET'])
def home():
    """API documentation"""
    return jsonify({
        'message': 'Blacklist Database API',
        'version': '1.0',
        'database_status': 'connected' if connection_pool else 'not configured',
        'endpoints': {
            'GET /health': 'Health check',
            'GET /api/blacklisted-users': 'Get all blacklisted users',
            'GET /api/blacklisted-users/<id>': 'Get specific user',
            'POST /api/blacklisted-users': 'Add user to blacklist',
            'DELETE /api/blacklisted-users/<id>': 'Remove user from blacklist',
            'GET /api/blacklisted-groups': 'Get all blacklisted groups',
            'GET /api/blacklisted-groups/<id>': 'Get specific group',
            'POST /api/blacklisted-groups': 'Add group to blacklist',
            'DELETE /api/blacklisted-groups/<id>': 'Remove group from blacklist',
            'GET /api/keywords/specific': 'Get specific keywords',
            'GET /api/keywords/nonspecific': 'Get nonspecific keywords',
            'GET /api/keywords/all': 'Get all keywords',
            'POST /api/keywords/check': 'Check text for keywords',
            'GET /api/realms-blacklist': 'Get realms blacklist',
            'GET /api/command-blacklist': 'Get command blacklist',
            'GET /api/search/user/<username>': 'Search for user',
            'GET /api/stats': 'Get database statistics'
        }
    })

# Clean up connection pool on shutdown
@app.teardown_appcontext
def close_pool(exception):
    if connection_pool:
        connection_pool.closeall()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"\n🚀 Starting Flask API on port {port}...")
    print(f"📍 Access at: http://127.0.0.1:{port}")
    print(f"🏥 Health check: http://127.0.0.1:{port}/health\n")
    app.run(host='0.0.0.0', port=port, debug=False)


