"""Job catalogue, searching and skill-match business rules."""
import json
from pathlib import Path
from models.mongo_database import MONGO_URI, jobs as mongo_jobs

def job_catalogue():
    if MONGO_URI:
        return mongo_jobs()
    path = Path(__file__).resolve().parents[1] / 'data/jobs.json'
    return json.loads(path.read_text(encoding='utf-8'))

def get_job(job_id):
    return next((dict(job) for job in job_catalogue() if str(job['id']) == str(job_id)), None)
def rank_jobs(skills, query='', location='', sort='match', only_matches=False):
    results = []
    for job in job_catalogue():
        if location and job['location'] != location:
            continue
        searchable = ' '.join([job['title'], job['company'], *job['skills']]).lower()
        if query.lower() not in searchable:
            continue
        item = dict(job)
        item['matched'] = [s for s in job['skills'] if s in skills]
        item['missing'] = [s for s in job['skills'] if s not in skills]
        item['score'] = int(len(item['matched']) / len(job['skills']) * 100 + 0.5) if job['skills'] else 0
        if not only_matches or item['matched']:
            results.append(item)
    return sorted(results, key=(lambda j: j['title']) if sort == 'title' else (lambda j: -j['score']))
