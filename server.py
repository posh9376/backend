from flask import Flask, request, jsonify
import psycopg2
import bcrypt
from flask_cors import CORS

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

# Test database connection
def test_db_connection():
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        cursor.execute('SELECT NOW()')
        print('✅ Database connected successfully')
        
        # Create table if not exists
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
        print('✅ Users table ready')
        cursor.close()
        conn.close()
    except Exception as err:
        print(f'❌ Database connection failed: {err}')

# Call test_db_connection function to initialize the database
test_db_connection()

@app.route('/')
def root():
    return 'Server is running!'

@app.route('/store-credentials', methods=['POST'])
async def store_credentials():
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

        # Insert user into the database
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        insert_query = 'INSERT INTO users (email, password) VALUES (%s, %s) RETURNING *'
        cursor.execute(insert_query, (email, hashed_password))
        user = cursor.fetchone()
        conn.commit()

        cursor.close()
        conn.close()

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
