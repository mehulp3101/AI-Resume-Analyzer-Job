from models.resume_model import extract_skills
from models.job_model import rank_jobs
from models.session_model import set_skills
from views.renderer import page, esc, tags, cards, no_skills, no_recommendations

def analyzer(session, query, form):
    return render(session)
def render(session, text='', message='', skills=None, code=200):
    found = skills if skills is not None else session['skills']
    recommendations = cards(rank_jobs(found, only_matches=True), session, True, '/analyzer') if found else no_recommendations()
    return code, page('analyzer.html', 'Resume analyzer', '/analyzer', session,
        resume=esc(text), message=esc(message), skills=tags(found) or no_skills(), recommendations=recommendations)
def analyze(session, query, form):
    text=form.get('resume','').strip()
    if not text:
        return render(session, message='Paste your resume text or choose a PDF or TXT file.', code=400)
    if len(text)>200000:
        return render(session, message='Resume must be at most 200,000 characters.', code=400)
    skills=extract_skills(text)
    set_skills(session, skills)
    return render(session, text, f'Analysis complete: {len(skills)} recognized skills.', skills)
def clear_skills(session, query, form):
    set_skills(session, [])
    return 303, '/jobs'


def extract_pdf(data):
    """Handle the PDF extraction request before normal resume analysis."""
    from models.pdf_model import extract_pdf_text
    try:
        return 200, {'text': extract_pdf_text(data)}
    except ModuleNotFoundError as error:
        if error.name != 'pypdf':
            raise
        return 503, {'error': 'PDF support needs pypdf. Run pip install -r requirements.txt and restart the app.'}
    except ValueError as error:
        return 400, {'error': str(error)}
