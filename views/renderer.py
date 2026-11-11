from html import escape
from pathlib import Path
from string import Template
from urllib.parse import urlencode
ROOT = Path(__file__).resolve().parent
def esc(value):
    return escape(str(value), quote=True)
def template(template_file, **values):
    return Template((ROOT / template_file).read_text(encoding="utf-8")).substitute(values)
def tags(skills):
    return ''.join('<span class="tag">'+esc(s)+'</span>' for s in skills)
def save_action(job_id, session, return_to):
    if not session.get('user'):
        return '<a class="button secondary" href="/login?'+esc(urlencode({'next':return_to}))+'">Log in to save</a>'
    return template('save_action.html', csrf=esc(session['csrf']),id=job_id,return_to=esc(return_to),save_label='Remove saved job' if job_id in session['saved'] else 'Save job')
def cards(jobs, session, show_score=False, return_to='/jobs'):
    if not jobs:
        return '<div class="empty">No jobs to display. Try another search or explore the Jobs page.</div>'
    return ''.join(template('card.html', title=esc(j['title']), company=esc(j['company']),
        location=esc(j['location']), description=esc(j['description']), skills=tags(j['skills']),
        score=(f'<p class="score">{j["score"]}% required skill overlap</p>' if show_score else ''),
        id=j['id'],save_action=save_action(j['id'],session,return_to)) for j in jobs)
def page(template_file, page_title, active, session, **values):
    links=[('/', 'Home'),('/analyzer','Resume analyzer'),('/jobs','Jobs'),('/saved','Saved jobs'),('/about','About')]
    nav=''.join('<a href="'+href+'"'+(' aria-current="page"' if href==active else '')+'>'+label+'</a>' for href,label in links)
    if session.get('user'):
        nav+='<span class="account-name">'+esc(session['user']['name'])+'</span><form class="logout-form" action="/logout" method="post"><input type="hidden" name="csrf" value="'+esc(session['csrf'])+'"><button class="secondary">Log out</button></form>'
    else:
        nav+=''.join('<a href="'+href+'"'+(' aria-current="page"' if active==href else '')+'>'+label+'</a>' for href,label in [('/login','Log in'),('/signup','Sign up')])
    content=template(template_file, csrf=esc(session['csrf']), **values)
    return template('layout.html', title=esc(page_title), navigation=nav, content=content).encode('utf-8')

def select_options(items, selected):
    return ''.join('<option value="'+esc(value)+'"'+(' selected' if selected==value else '')+'>'+esc(label)+'</option>' for value,label in items)
def match_summary(result, has_skills):
    if not has_skills:
        return '<p>Analyze your resume to see your match.</p><p><a href="/analyzer">Open analyzer</a></p>'
    return ('<p class="score">'+str(result['score'])+'% required skill overlap</p><p>Matched: '+esc(', '.join(result['matched']) or 'None')+'</p><p>Skills to develop: '+esc(', '.join(result['missing']) or 'All listed skills matched')+'</p>')
def no_skills():
    return '<p>No recognized skills yet.</p>'
def no_recommendations():
    return '<p>Analyze resume text to see recommendations.</p>'