import os
import sys

# Ensure root directory is on sys.path so modules like app, database, etc. can be imported
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from urllib.parse import parse_qs, urlencode
from app import app

class VercelPathFixMiddleware:
    """
    Normalizes WSGI environment variables when deployed behind Vercel serverless rewrites.
    Restores the true client PATH_INFO and clean QUERY_STRING so all Flask routes work seamlessly.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        query_string = environ.get('QUERY_STRING', '')
        if '__vercel_path' in query_string:
            params = parse_qs(query_string, keep_blank_values=True)
            if '__vercel_path' in params:
                raw_path = params.pop('__vercel_path')[0]
                environ['QUERY_STRING'] = urlencode(params, doseq=True)
                clean_path = '/' + raw_path.lstrip('/')
                environ['PATH_INFO'] = clean_path
                clean_qs = environ['QUERY_STRING']
                environ['RAW_URI'] = clean_path + (('?' + clean_qs) if clean_qs else '')
                environ['REQUEST_URI'] = environ['RAW_URI']
                return self.wsgi_app(environ, start_response)

        # 1. Fallback: check if the original client request URI was forwarded in headers
        request_uri = (
            environ.get('HTTP_X_FORWARDED_URI')
            or environ.get('HTTP_X_VERCEL_FORWARDED_URI')
            or environ.get('REQUEST_URI')
            or ''
        )
        if request_uri:
            path_only = request_uri.split('?')[0]
            if path_only and not path_only.startswith('/api/index'):
                environ['PATH_INFO'] = path_only

        # 2. Normalize Vercel rewrite entry point path artifacts
        path_info = environ.get('PATH_INFO', '')
        if path_info in ('/api/index', '/api/index.py', '/api', '/api/'):
            environ['PATH_INFO'] = '/'
        elif path_info.startswith('/api/index/'):
            clean_path = path_info[len('/api/index'):]
            environ['PATH_INFO'] = clean_path if clean_path.startswith('/') else '/' + clean_path
        elif path_info.startswith('/api/index.py/'):
            clean_path = path_info[len('/api/index.py'):]
            environ['PATH_INFO'] = clean_path if clean_path.startswith('/') else '/' + clean_path

        return self.wsgi_app(environ, start_response)

# Apply WSGI path normalization middleware
app.wsgi_app = VercelPathFixMiddleware(app.wsgi_app)
