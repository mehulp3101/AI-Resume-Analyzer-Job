"""Local learning server. Run: py server.py. No third-party packages."""
import argparse
import json
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import secrets
from routes import ROUTES
from controllers.resume_controller import extract_pdf
from models.pdf_model import MAX_PDF_BYTES
from models.session_model import open_session, rotate_session
from models.user_model import get_user
from models.saved_job_model import list_saved
from views.renderer import page
ROOT=Path(__file__).resolve().parent
MAX_BODY=1500000
class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Avoid logging resume bodies or search queries.
        pass
    def do_GET(self): self.handle_request('GET')
    def do_POST(self): self.handle_request('POST')
    def respond(self, code, content, session_id=None, content_type='text/html; charset=utf-8'):
        body=content if isinstance(content,bytes) else b''
        self.send_response(code)
        self.send_header('Content-Type',content_type)
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','same-origin')
        if session_id:
            self.send_header('Set-Cookie',f'rm_session={session_id}; HttpOnly; SameSite=Strict; Path=/')
        if code==303:self.send_header('Location',content)
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def handle_pdf(self, sid, session):
        def reply(status, payload):
            self.respond(status, json.dumps(payload).encode('utf-8'), sid, 'application/json; charset=utf-8')

        token = self.headers.get('X-CSRF-Token', '')
        if not secrets.compare_digest(token.encode('utf-8'), session['csrf'].encode('utf-8')):
            return reply(403, {'error': 'Reload the analyzer page and try again.'})
        if self.headers.get_content_type() != 'application/pdf':
            return reply(415, {'error': 'Choose a PDF resume.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            length = 0
        if length <= 0:
            return reply(400, {'error': 'The PDF is empty.'})
        if length > MAX_PDF_BYTES:
            return reply(413, {'error': 'The file is too large. Maximum size is 1 MB.'})
        status, result = extract_pdf(self.rfile.read(length))
        return reply(status, result)

    def handle_request(self, method):
        url=urlsplit(self.path)
        if method=='GET' and url.path.startswith('/public/'):
            static={'/public/style.css':('style.css','text/css'),'/public/analyzer.js':('analyzer.js','text/javascript')}
            if url.path in static:
                filename,mime=static[url.path]
                return self.respond(200,(ROOT/'public'/filename).read_bytes(),content_type=mime+'; charset=utf-8')
            return self.respond(404,b'Not found',content_type='text/plain')
        cookie=SimpleCookie()
        try:cookie.load(self.headers.get('Cookie',''))
        except CookieError:cookie=SimpleCookie()
        sid=cookie['rm_session'].value if 'rm_session' in cookie else None
        sid,session=open_session(sid)
        if session.get('user'):
            session['user']=get_user(session['user']['id'])
            session['saved']=list_saved(session['user']['id']) if session['user'] else []
        if method == 'POST' and url.path == '/analyzer/pdf':
            return self.handle_pdf(sid, session)
        form={}
        if method=='POST':
            try:length=int(self.headers.get('Content-Length','0'))
            except ValueError:length=-1
            if not 0<=length<=MAX_BODY:
                return self.respond(413,b'Request too large',sid, 'text/plain')
            try:form={k:v[0] for k,v in parse_qs(self.rfile.read(length).decode('utf-8'),keep_blank_values=True).items()}
            except UnicodeDecodeError:return self.respond(400,b'Invalid text encoding',sid,'text/plain')
            if not secrets.compare_digest(form.get('csrf','').encode('utf-8'), session['csrf'].encode('utf-8')):
                return self.respond(403,b'Invalid form token. Reload the page and try again.',sid,'text/plain')
        action=ROUTES.get((method,url.path))
        query={k:v[0] for k,v in parse_qs(url.query,keep_blank_values=True).items()}
        try:
            code,content=action(session,query,form) if action else (404,page('error.html','Page not found','',session,heading='Page not found',message='Use navigation to open a page.'))
        except Exception:
            import traceback
            traceback.print_exc()
            code,content=500,page('error.html','Server error','',session,heading='Could not load this page',message='Under maintenance.')
        if session.pop('_rotate',False):sid=rotate_session(sid,session)
        self.respond(code,content,sid)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8000);args=parser.parse_args()
    from models.mongo_database import MONGO_URI, MONGO_DATABASE, users
    if MONGO_URI:
        try:
            from pymongo.errors import PyMongoError
        except ImportError:
            raise SystemExit('Install dependencies with python -m pip install -r requirements.txt.') from None
        try:
            users()
        except (PyMongoError, ValueError):
            raise SystemExit('MongoDB setup failed. Check MONGODB_URI, your Atlas database user, and your Atlas network access settings.') from None
        print(f'MongoDB account storage ready: {MONGO_DATABASE}', flush=True)
    server=HTTPServer(('127.0.0.1',args.port),Handler)
    print(f'ResumeMatch MVC running at http://127.0.0.1:{args.port}',flush=True)
    print('Keep this terminal open. Press Ctrl+C to stop.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:print('\nServer stopped.')
    finally:server.server_close()
