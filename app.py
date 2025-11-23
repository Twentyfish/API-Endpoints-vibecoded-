from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

app = Flask(__name__)
CORS(app)

# PostgreSQL connection
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """Create a database connection"""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def dict_cursor_conn():
    """Get connection with dict cursor"""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

# ==================== BLACKLISTED USERS ====================

@app.route('/api/blacklisted-users', methods=['GET'])
def get_blacklisted_users():
    """Get all blacklisted users"""
    conn = dict_cursor_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM blacklisted_users')
    users = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(user) for user in users])

@app.route('/api/blacklisted-users/<int:user_id>', methods=['GET'])
def get_blacklisted_user(user_id):
    """Get specific blacklisted user by ID"""
    conn = dict_cursor_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM blacklisted_users WHERE user_id = %s', (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    if user is None:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(dict(user))

@app.route('/api/blacklisted-users', methods=['POST'])
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
        cur.close()
        conn.close()
        return jsonify({'message': 'User added to blacklist', 'user_id': user_id}), 201
    except psycopg2.IntegrityError:
        cur.close()
        conn.close()
        return jsonify({'error': 'User already exists in blacklist'}), 409

@app.route('/api/blacklisted-users/<int:user_id>', methods=['DELETE'])
def remove_blacklisted_user(user_id):
    """Remove a user from blacklist"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM blacklisted_users WHERE user_id = %s', (user_id,))
    rowcount = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    
    if rowcount == 0:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'message': 'User removed from blacklist'})

# ==================== BLACKLISTED GROUPS ====================

@app.route('/api/blacklisted-groups', methods=['GET'])
def get_blacklisted_groups():
    """Get all blacklisted groups"""
    conn = dict_cursor_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM blacklisted_groups')
    groups = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(group) for group in groups])

@app.route('/api/blacklisted-groups/<int:group_id>', methods=['GET'])
def get_blacklisted_group(group_id):
    """Get specific blacklisted group by ID"""
    conn = dict_cursor_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM blacklisted_groups WHERE group_id = %s', (group_id,))
    group = cur.fetchone()
    cur.close()
    conn.close()
    
    if group is None:
        return jsonify({'error': 'Group not found'}), 404
    
    return jsonify(dict(group))

@app.route('/api/blacklisted-groups', methods=['POST'])
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
        cur.close()
        conn.close()
        return jsonify({'message': 'Group added to blacklist', 'group_id': group_id}), 201
    except psycopg2.IntegrityError:
        cur.close()
        conn.close()
        return jsonify({'error': 'Group already exists in blacklist'}), 409

# ==================== FLAGGED KEYWORDS ====================

@app.route('/api/keywords/specific', methods=['GET'])
def get_specific_keywords():
    """Get all specific flagged keywords"""
    conn = dict_cursor_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM flagged_keywords_specific')
    keywords = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(kw) for kw in keywords])

@app.route('/api/keywords/nonspecific', methods=['GET'])
def get_nonspecific_keywords():
    """Get all nonspecific flagged keywords"""
    conn = dict_cursor_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM flagged_keywords_nonspecific')
    keywords = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(kw) for kw in keywords])

@app.route('/api/keywords/all', methods=['GET'])
def get_all_keywords():
    """Get all flagged keywords from both tables"""
    conn = dict_cursor_conn()
    cur = conn.cursor()
    cur.execute('SELECT *, \'specific\' as type FROM flagged_keywords_specific')
    specific = cur.fetchall()
    cur.execute('SELECT *, \'nonspecific\' as type FROM flagged_keywords_nonspecific')
    nonspecific = cur.fetchall()
    cur.close()
    conn.close()
    
    all_keywords = [dict(kw) for kw in specific] + [dict(kw) for kw in nonspecific]
    return jsonify(all_keywords)

@app.route('/api/keywords/check', methods=['POST'])
def check_text_for_keywords():
    """Check if text contains any flagged keywords"""
    data = request.get_json()
    text = data.get('text', '').lower()
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    conn = dict_cursor_conn()
    cur = conn.cursor()
    cur.execute('SELECT keyword FROM flagged_keywords_specific')
    specific = cur.fetchall()
    cur.execute('SELECT keyword FROM flagged_keywords_nonspecific')
    nonspecific = cur.fetchall()
    cur.close()
    conn.close()
    
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

# ==================== REALMS & COMMAND BLACKLIST ====================

@app.route('/api/realms-blacklist', methods=['GET'])
def get_realms_blacklist():
    """Get all users on realms blacklist"""
    conn = dict_cursor_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM realms_blacklist')
    users = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(user) for user in users])

@app.route('/api/command-blacklist', methods=['GET'])
def get_command_blacklist():
    """Get all users on command blacklist"""
    conn = dict_cursor_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM command_blacklist')
    users = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(user) for user in users])

# ==================== SEARCH & UTILITY ====================

@app.route('/api/search/user/<username>', methods=['GET'])
def search_user(username):
    """Search for a user across all blacklist tables"""
    conn = dict_cursor_conn()
    cur = conn.cursor()
    
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
    
    cur.close()
    conn.close()
    
    return jsonify(results)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics about the database"""
    conn = get_db_connection()
    cur = conn.cursor()
    
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
    
    cur.close()
    conn.close()
    return jsonify(stats)

@app.route('/', methods=['GET'])
def home():
    """API documentation"""
    return jsonify({
        'message': 'Blacklist Database API',
        'endpoints': {
            'GET /api/blacklisted-users': 'Get all blacklisted users',
            'GET /api/blacklisted-users/<id>': 'Get specific user',
            'POST /api/blacklisted-users': 'Add user to blacklist',
            'DELETE /api/blacklisted-users/<id>': 'Remove user from blacklist',
            'GET /api/blacklisted-groups': 'Get all blacklisted groups',
            'GET /api/blacklisted-groups/<id>': 'Get specific group',
            'POST /api/blacklisted-groups': 'Add group to blacklist',
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

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
