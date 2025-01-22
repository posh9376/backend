from flask import Flask, request, jsonify
import psycopg2
import bcrypt
from flask_cors import CORS
from psycopg2 import pool

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS

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

# Function to initialize database connection pool
def init_db_pool():
    global db_pool
    if db_pool is None:
        db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, **db_params)
        print('✅ Database connection pool initialized')

# Test database connection at startup
def test_db_connection():
    try:
        conn = db_pool.getconn()  # Get connection from the pool
        cursor = conn.cursor()
        cursor.execute('SELECT NOW()')
        print('✅ Database connected successfully')

        # Create table if it doesn't exist
        create_table_query = '''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        '''
        cursor.execute(create_table_query)
        conn.commit()
        cursor.close()
        db_pool.putconn(conn)  # Return connection to the pool
        print('✅ Users table ready')

    except Exception as err:
        print(f'❌ Database connection failed: {err}')

# Call init_db_pool and test_db_connection at the app startup
init_db_pool()
test_db_connection()

@app.route('/')
def root():
    return 'Server is running!'

@app.route('/store-credentials', methods=['POST'])
def store_credentials():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        print('❌ Missing email or password')
        return jsonify({
            'error': 'Email and password are required',
            'shouldNavigate': False
        }), 400

    try:
        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Get connection from pool
        conn = db_pool.getconn()
        cursor = conn.cursor()

        # Insert user into the database
        insert_query = 'INSERT INTO users (email, password) VALUES (%s, %s) RETURNING *'
        cursor.execute(insert_query, (email, hashed_password))
        user = cursor.fetchone()
        conn.commit()

        # Close cursor and return connection to pool
        cursor.close()
        db_pool.putconn(conn)

        print(f'✅ User stored successfully: {user}')

        # Send back response
        return jsonify({
            'success': True,
            'message': 'User stored successfully',
            'user': {'id': user[0], 'email': user[1]},
            'shouldNavigate': True,
            'navigateTo': '/verification'  # or wherever you want to navigate
        }), 200

    except Exception as err:
        print(f'❌ Database error: {err}')
        return jsonify({
            'success': False,
            'error': 'Error saving credentials',
            'details': str(err),
            'shouldNavigate': False
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5020)
