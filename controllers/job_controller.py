from models.job_model import get_job, rank_jobs
from models.session_model import toggle_job
from views.renderer import page, esc, tags, cards, select_options, match_summary, save_action

def browse(session, query, form):
    q=query.get('q',''); location=query.get('location',''); sort=query.get('sort','match')
    jobs=rank_jobs(session['skills'],q,location,sort)
    options=select_options([(loc,loc or 'All locations') for loc in ['', 'Tauranga','Auckland','Hamilton','Remote NZ']],location)
    sorts=select_options([('match','Best match'),('title','Title A–Z')],sort)
    return 200,page('jobs.html','Jobs','/jobs',session,query=esc(q),locations=options,sort_options=sorts,count=len(jobs),profile=esc('Detected skills: '+', '.join(session['skills']) if session['skills'] else 'Analyze your resume to enable skill match scores.'),jobs=cards(jobs,session,bool(session['skills'])))
def detail(session, query, form):
    job=get_job(query.get('id'))
    if not job:
        return 404,page('error.html','Job not found','/jobs',session,heading='Job not found',message='Return to Jobs to choose a sample role.')
    result=next(j for j in rank_jobs(session['skills']) if j['id']==job['id'])
    match=match_summary(result,bool(session['skills']))
    return 200,page('job.html',job['title'],'/jobs',session,title=esc(job['title']),company=esc(job['company']),location=esc(job['location']),description=esc(job['description']),skills=tags(job['skills']),match=match,id=job['id'],save_action=save_action(job['id'],session,f'/job?id={job["id"]}'))
def saved(session, query, form):
    if not session.get('user'):return 303,'/login?next=/saved'
    jobs=[j for j in rank_jobs(session['skills']) if j['id'] in session['saved']]
    return 200,page('saved.html','Saved jobs','/saved',session,count=len(jobs),jobs=cards(jobs,session,bool(session['skills']),'/saved'))
def toggle(session, query, form):
    if not session.get('user'):return 303,'/login?next=/saved'
    job=get_job(form.get('id'))
    if not job:
        return 404,page('error.html','Job not found','/jobs',session,heading='Job not found',message='Choose a valid sample job.')
    toggle_job(session,job['id'])
    target=form.get('return_to','/saved')
    allowed=['/saved','/jobs','/analyzer',f'/job?id={job["id"]}']
    return 303,target if target in allowed else '/saved'
