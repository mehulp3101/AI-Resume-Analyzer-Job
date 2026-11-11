"""Run from the project folder: py -m unittest discover -s tests -v"""
import http.cookiejar
import re
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import HTTPServer
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import build_opener, HTTPCookieProcessor, Request
from models import database, auth_attempt_model, session_model
from models.resume_model import extract_skills
from models.job_model import rank_jobs
from models.user_model import create_user, authenticate, verify_password
from server import Handler

PASSWORD='A unique test passphrase 42'

class ModelTests(unittest.TestCase):
    def test_aliases_and_boundaries(self):
        self.assertEqual(extract_skills('React.js, Node.js, MySQL and CSS3'),['CSS','React','SQL','Node.js'])
        self.assertEqual(extract_skills('fishing, shopping'),[])
    def test_ranking(self):
        result=rank_jobs(['Python','SQL','Git'])[0]
        self.assertEqual(result['title'],'Python Backend Developer')
        self.assertEqual(result['score'],100)
        self.assertEqual(len(rank_jobs([],query='Python')),1)
        self.assertTrue(all(j['location']=='Tauranga' for j in rank_jobs([],location='Tauranga')))

class AccountWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.original_db=database.DB_PATH
        database.DB_PATH=Path(cls.temp.name)/'test.sqlite3'
        cls.server=HTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
        database.DB_PATH=cls.original_db
        cls.temp.cleanup()
    def setUp(self):
        auth_attempt_model.ATTEMPTS.clear()
        session_model.SESSIONS.clear()
        self.jar=http.cookiejar.CookieJar()
        self.client=build_opener(HTTPCookieProcessor(self.jar))
    def request(self,path,form=None,client=None):
        req=Request(self.base+path,data=urlencode(form).encode() if form is not None else None)
        try:response=(client or self.client).open(req)
        except HTTPError as error:response=error
        with response:return response.status,response.read().decode(),response.geturl()
    def token(self,path='/login'):
        _,body,_=self.request(path)
        return re.search(r'name="csrf" value="([^"]+)"',body).group(1)
    def csrf_cookie(self):
        return next(cookie.value for cookie in self.jar if cookie.name=='rm_session')
    def signup(self,email,next_to='/jobs'):
        token=self.token('/signup')
        return self.request('/signup',{'csrf':token,'name':'Test Student','email':email,'password':PASSWORD,'confirmation':PASSWORD,'next':next_to})
    def logout(self):
        return self.request('/logout',{'csrf':self.token('/jobs')})
    def login(self,email,password=PASSWORD,next_to='/jobs'):
        return self.request('/login',{'csrf':self.token(),'email':email,'password':password,'next':next_to})
    def test_public_pages_and_auth_forms(self):
        for path in ['/','/analyzer','/jobs','/job?id=0','/about','/login','/signup']:
            self.assertEqual(self.request(path)[0],200)
        status,body,url=self.request('/saved')
        self.assertEqual(status,200);self.assertIn('/login',url)
        self.assertIn('Log in to save',self.request('/job?id=0')[1])
    def test_signup_login_logout_and_session_rotation(self):
        old_token=self.token('/signup');old_sid=self.csrf_cookie()
        status,body,url=self.signup('rotation@example.com')
        self.assertEqual(status,200);self.assertTrue(url.endswith('/jobs'))
        self.assertIn('Test Student',body);self.assertIn('Log out',body)
        self.assertNotEqual(old_sid,self.csrf_cookie())
        self.assertNotIn(old_sid,session_model.SESSIONS)
        self.assertEqual(self.request('/logout',{'csrf':old_token})[0],403)
        self.logout()
        self.assertIn('Log in',self.request('/')[1]);self.assertNotIn('Log out',self.request('/')[1])
        status,body,_=self.login('ROTATION@example.com')
        self.assertEqual(status,200);self.assertIn('Log out',body)
    def test_registration_validation_and_duplicates(self):
        token=self.token('/signup')
        form={'csrf':token,'name':'<b>Student</b>','email':'bad-email','password':'short','confirmation':'different'}
        code,body,_=self.request('/signup',form)
        self.assertEqual(code,400);self.assertIn('&lt;b&gt;',body);self.assertNotIn('value="short"',body)
        form.update(email='validation@example.com')
        self.assertIn('10 and 128',self.request('/signup',form)[1])
        form.update(password=PASSWORD)
        self.assertIn('do not match',self.request('/signup',form)[1])
        self.signup('duplicate@example.com');self.logout()
        self.assertEqual(self.signup('DUPLICATE@example.com')[0],400)
        self.assertIn('already registered',self.signup('duplicate@example.com')[1])
    def test_password_storage_and_verification(self):
        user1=create_user('First Student','hash-one@example.com',PASSWORD,PASSWORD)
        user2=create_user('Second Student','hash-two@example.com',PASSWORD,PASSWORD)
        db=database.connect()
        try:
            a=db.execute('SELECT password_hash FROM users WHERE id=?',(user1['id'],)).fetchone()[0]
            b=db.execute('SELECT password_hash FROM users WHERE id=?',(user2['id'],)).fetchone()[0]
        finally:db.close()
        self.assertNotEqual(a,b);self.assertNotEqual(a,PASSWORD)
        self.assertTrue(verify_password(PASSWORD,a));self.assertFalse(verify_password('wrong password',a))
        self.assertIsNone(authenticate('missing@example.com',PASSWORD))
    def test_bad_login_throttle_and_csrf(self):
        self.assertEqual(self.request('/login',{'email':'none@example.com','password':PASSWORD})[0],403)
        for _ in range(5):
            code,body,_=self.login('unknown@example.com','wrong-password')
            self.assertEqual(code,401);self.assertIn('Email or password is incorrect',body)
        self.assertEqual(self.login('unknown@example.com','wrong-password')[0],429)
        token=self.token('/login')
        self.assertEqual(self.request('/logout',{'csrf':'é'+token})[0],403)
    def test_per_user_saved_jobs_persist_after_sessions_reset(self):
        self.signup('owner@example.com')
        token=self.token('/jobs')
        code,body,_=self.request('/saved/toggle',{'csrf':token,'id':'2','return_to':'/saved'})
        self.assertEqual(code,200);self.assertIn('1 saved jobs.',body)
        self.logout();self.signup('other@example.com')
        self.assertIn('0 saved jobs.',self.request('/saved')[1])
        self.logout();session_model.SESSIONS.clear()
        self.login('owner@example.com',next_to='/saved')
        self.assertIn('1 saved jobs.',self.request('/saved')[1])
        token=self.token('/saved')
        self.assertIn('0 saved jobs.',self.request('/saved/toggle',{'csrf':token,'id':'2','return_to':'/saved'})[1])
    def test_analyzer_search_and_errors(self):
        token=self.token('/analyzer')
        status,body,_=self.request('/analyze',{'csrf':token,'resume':'Python SQL Git <script>alert(1)</script>'})
        self.assertEqual(status,200);self.assertIn('100% required skill overlap',body)
        self.assertIn('&lt;script&gt;',body);self.assertNotIn('<script>alert(1)</script>',body)
        self.assertIn('1 sample jobs found.',self.request('/jobs?q=Python')[1])
        self.assertEqual(self.request('/job?id=invalid')[0],404)
        self.assertEqual(self.request('/analyze',{'csrf':token,'resume':' '})[0],400)
        self.assertEqual(self.request('/analyze',{'resume':'Python'})[0],403)
    def test_redirect_target_allowlist(self):
        _,_,url=self.signup('redirect@example.com',next_to='https://example.com')
        self.assertTrue(url.endswith('/jobs'))

if __name__=='__main__':unittest.main()
