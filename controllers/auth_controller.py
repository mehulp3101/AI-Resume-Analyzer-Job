"""Account routes coordinate user/session models with authentication views."""
import re

from models.user_model import create_user, authenticate, normalize_email
from models.saved_job_model import list_saved
from models import auth_attempt_model as attempts
from views.renderer import page, esc

def safe_next(value):
    allowed={'/','/analyzer','/jobs','/saved','/about'}
    if value in allowed or (isinstance(value, str) and re.fullmatch(r'/job\?id=[0-9]+', value)):
        return value
    return '/jobs'

def form_page(kind, session, next_to='/jobs', message='', name='', email='', code=200):
    return code,page(kind+'.html','Log in' if kind=='login' else 'Sign up','/'+kind,session,
        message=esc(message),name=esc(name),email=esc(email),next_to=esc(safe_next(next_to)))

def login_page(session,query,form):
    if session.get('user'):return 303,safe_next(query.get('next'))
    return form_page('login',session,query.get('next','/jobs'))

def signup_page(session,query,form):
    if session.get('user'):return 303,safe_next(query.get('next'))
    return form_page('signup',session,query.get('next','/jobs'))

def establish_login(session,user):
    session['user']=user
    session['saved']=list_saved(user['id'])
    session['_rotate']=True

def signup(session,query,form):
    if session.get('user'):return 303,'/jobs'
    name=form.get('name','');email=form.get('email','');next_to=form.get('next','/jobs')
    try:user=create_user(name,email,form.get('password',''),form.get('confirmation',''))
    except ValueError as error:return form_page('signup',session,next_to,str(error),name,email,400)
    establish_login(session,user)
    return 303,safe_next(next_to)

def login(session,query,form):
    if session.get('user'):return 303,'/jobs'
    email=form.get('email','');password=form.get('password','');next_to=form.get('next','/jobs')
    # Limit per email and per browser; the local server is not a production auth service.
    keys=('email:'+normalize_email(email), 'browser:'+session['csrf'])
    if any(attempts.blocked(key) for key in keys):
        return form_page('login',session,next_to,'Too many unsuccessful attempts. Please try again in five minutes.',email=email,code=429)
    if not email.strip() or not password:
        return form_page('login',session,next_to,'Enter your email and password.',email=email,code=400)
    user=authenticate(email,password)
    if not user:
        for key in keys:attempts.failed(key)
        return form_page('login',session,next_to,'Email or password is incorrect.',email=email,code=401)
    for key in keys:attempts.succeeded(key)
    establish_login(session,user)
    return 303,safe_next(next_to)

def logout(session,query,form):
    session.update(user=None,skills=[],saved=[],_rotate=True)
    return 303,'/'
