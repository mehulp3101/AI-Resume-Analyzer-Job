"""In-memory sessions expire after two idle hours; accounts live in SQLite."""
import secrets
import time
from models.saved_job_model import list_saved, toggle_saved
SESSIONS = {}
TTL = 7200

def open_session(session_id):
    now=time.time()
    for key in list(SESSIONS):
        if now-SESSIONS[key]['updated']>TTL:del SESSIONS[key]
    if session_id not in SESSIONS:
        session_id=secrets.token_urlsafe(32)
        SESSIONS[session_id]={'skills':[],'saved':[],'csrf':secrets.token_urlsafe(32),'user':None}
    SESSIONS[session_id]['updated']=now
    return session_id,SESSIONS[session_id]

def rotate_session(old_id, session):
    SESSIONS.pop(old_id,None)
    new_id=secrets.token_urlsafe(32)
    session.pop('_rotate',None)
    session['csrf']=secrets.token_urlsafe(32)
    session['updated']=time.time()
    SESSIONS[new_id]=session
    return new_id

def set_skills(session,skills):session['skills']=list(skills)

def toggle_job(session,job_id):
    if not session.get('user'):raise ValueError('Login required')
    toggle_saved(session['user']['id'],job_id)
    session['saved']=list_saved(session['user']['id'])
