#!/usr/bin/env python3
"""
Secure Microservices Worker - Python/Flask Version
"""

import os
import sys
import logging
import json
import time
from datetime import datetime
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import psycopg2
import redis

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/app/app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

DB_HOST = os.getenv('DB_HOST', 'database')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_USER = os.getenv('DB_USER', 'myapp_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'secure_password_here')
DB_NAME = os.getenv('DB_NAME', 'myapp')
CACHE_HOST = os.getenv('CACHE_HOST', 'cache')
CACHE_PORT = int(os.getenv('CACHE_PORT', 6379))
CACHE_PASSWORD = os.getenv('CACHE_PASSWORD', 'secure_cache_password_here')
API_PORT = int(os.getenv('API_PORT', 8080))

# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per minute", "1000 per hour"],
)

# ============================================================
# DATABASE
# ============================================================

def get_db():
    if not hasattr(g, 'db_conn'):
        try:
            g.db_conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                dbname=DB_NAME
            )
            g.db_conn.autocommit = False
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    return g.db_conn

def query_db(query, params=None, commit=False):
    """Execute a query and return results"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params or ())
        
        # For SELECT queries, fetch and return results
        if query.strip().upper().startswith('SELECT'):
            results = cursor.fetchall()
            cursor.close()
            return results
        
        # For INSERT/UPDATE/DELETE
        if commit:
            conn.commit()
            # If RETURNING clause, fetch results
            if 'RETURNING' in query.upper():
                results = cursor.fetchall()
                cursor.close()
                return results
            cursor.close()
            return True
        
        cursor.close()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Query error: {e}")
        raise

# ============================================================
# CACHE
# ============================================================

def get_cache():
    if not hasattr(g, 'cache_client'):
        try:
            g.cache_client = redis.Redis(
                host=CACHE_HOST,
                port=CACHE_PORT,
                password=CACHE_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            g.cache_client.ping()
        except Exception as e:
            logger.warning(f"Cache connection failed: {e}")
            g.cache_client = None
    return g.cache_client

def cache_get(key):
    cache = get_cache()
    if cache:
        try:
            value = cache.get(key)
            if value:
                return json.loads(value)
        except:
            pass
    return None

def cache_set(key, value, ttl=3600):
    cache = get_cache()
    if cache:
        try:
            cache.setex(key, ttl, json.dumps(value))
        except:
            pass

def cache_delete(key):
    cache = get_cache()
    if cache:
        try:
            cache.delete(key)
        except:
            pass

# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_database():
    """Create tables if they don't exist"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cursor.close()
        logger.info("✅ Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

# ============================================================
# API ENDPOINTS
# ============================================================

@app.route('/health', methods=['GET'])
def health_check():
    status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'uptime': time.time() - start_time,
        'services': {'database': False, 'cache': False}
    }
    
    try:
        query_db("SELECT 1")
        status['services']['database'] = True
    except:
        pass
    
    try:
        cache = get_cache()
        if cache:
            cache.ping()
            status['services']['cache'] = True
    except:
        pass
    
    all_healthy = all(status['services'].values())
    status['status'] = 'healthy' if all_healthy else 'unhealthy'
    return jsonify(status), 200 if all_healthy else 503

@app.route('/api/users', methods=['POST'])
@limiter.limit("10 per minute")
def create_user():
    """Create a new user"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing JSON body'}), 400
        
        username = data.get('username')
        email = data.get('email')
        
        if not username or not email:
            return jsonify({'error': 'Username and email are required'}), 400
        
        if '@' not in email or '.' not in email.split('@')[-1]:
            return jsonify({'error': 'Invalid email format'}), 400
        
        logger.info(f"Creating user: {username} - {email}")
        
        # Insert user with RETURNING
        results = query_db(
            "INSERT INTO users (username, email) VALUES (%s, %s) RETURNING id, username, email, created_at",
            [username, email],
            commit=True
        )
        
        if results and len(results) > 0:
            row = results[0]
            user_dict = {
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'created_at': row[3].isoformat() if row[3] else None
            }
            
            # Cache the user
            cache_set(f"user:{user_dict['id']}", user_dict, 3600)
            
            logger.info(f"✅ User created: {username} (ID: {user_dict['id']})")
            return jsonify({'success': True, 'data': user_dict}), 201
        
        return jsonify({'error': 'Failed to create user'}), 500
        
    except psycopg2.IntegrityError as e:
        if 'unique' in str(e).lower():
            return jsonify({'error': 'Username or email already exists'}), 409
        logger.error(f"Integrity error: {e}")
        return jsonify({'error': 'Database constraint violation'}), 400
    except Exception as e:
        logger.error(f"❌ Error creating user: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get user by ID (with cache)"""
    try:
        # Try cache first
        cached_user = cache_get(f"user:{user_id}")
        if cached_user:
            logger.info(f"User {user_id} from cache")
            return jsonify({'success': True, 'data': cached_user, 'from_cache': True})
        
        # Get from database
        results = query_db(
            "SELECT id, username, email, created_at FROM users WHERE id = %s",
            [user_id]
        )
        
        if not results or len(results) == 0:
            return jsonify({'error': 'User not found'}), 404
        
        row = results[0]
        user_dict = {
            'id': row[0],
            'username': row[1],
            'email': row[2],
            'created_at': row[3].isoformat() if row[3] else None
        }
        
        # Cache for next time
        cache_set(f"user:{user_id}", user_dict, 3600)
        
        logger.info(f"User {user_id} from database")
        return jsonify({'success': True, 'data': user_dict, 'from_cache': False})
        
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/users', methods=['GET'])
def get_all_users():
    """Get all users"""
    try:
        results = query_db(
            "SELECT id, username, email, created_at FROM users ORDER BY id"
        )
        
        users = []
        for row in results:
            users.append({
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'created_at': row[3].isoformat() if row[3] else None
            })
        
        return jsonify({
            'success': True,
            'data': users,
            'count': len(users)
        })
        
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user"""
    try:
        results = query_db(
            "DELETE FROM users WHERE id = %s RETURNING id",
            [user_id],
            commit=True
        )
        
        if not results or len(results) == 0:
            return jsonify({'error': 'User not found'}), 404
        
        # Delete from cache
        cache_delete(f"user:{user_id}")
        
        logger.info(f"User {user_id} deleted")
        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    """Get Redis cache statistics"""
    try:
        cache = get_cache()
        if not cache:
            return jsonify({'error': 'Cache not available'}), 503
        
        info = cache.info('stats')
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        hit_rate = (hits / (hits + misses) * 100) if (hits + misses) > 0 else 0
        
        return jsonify({
            'success': True,
            'data': {
                'cache_hits': hits,
                'cache_misses': misses,
                'hit_rate': f"{hit_rate:.2f}%",
                'ops_per_sec': info.get('instantaneous_ops_per_sec', 0)
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# ============================================================
# CLEANUP
# ============================================================

@app.teardown_appcontext
def close_connections(error):
    if hasattr(g, 'db_conn'):
        try:
            g.db_conn.close()
        except:
            pass
    if hasattr(g, 'cache_client'):
        try:
            g.cache_client.close()
        except:
            pass

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(429)
def rate_limit_exceeded(error):
    return jsonify({'error': 'Rate limit exceeded. Try again later.'}), 429

# ============================================================
# START APPLICATION
# ============================================================

start_time = time.time()

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Starting Secure Microservices Worker")
    print(f"📡 API: http://0.0.0.0:{API_PORT}")
    print(f"🔒 Database: {DB_HOST}:{DB_PORT}")
    print(f"🔒 Cache: {CACHE_HOST}:{CACHE_PORT}")
    print("🛡️  Security: Internal network isolation enabled")
    print("=" * 60)
    
    with app.app_context():
        init_database()
    
    app.run(
        host='0.0.0.0',
        port=API_PORT,
        debug=False,
        threaded=True
    )
