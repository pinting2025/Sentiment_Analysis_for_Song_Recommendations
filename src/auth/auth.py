from functools import wraps
from flask import request, jsonify
import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_API_KEY = os.getenv('ADMIN_API_KEY')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != ADMIN_API_KEY:
            return jsonify({'error': 'Unauthorized access. Admin privileges required.'}), 403
        return f(*args, **kwargs)
    return decorated_function 