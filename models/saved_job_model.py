"""Each registered user's shortlist persists independently in the configured database."""
from models.database import connect
from models.mongo_database import MONGO_URI, users

def list_saved(user_id):
    if MONGO_URI:
        user = users().find_one({'_id': user_id}, {'saved_jobs': 1})
        return sorted(user.get('saved_jobs', [])) if user else []
    db=connect()
    try:return [row['job_id'] for row in db.execute('SELECT job_id FROM saved_jobs WHERE user_id=? ORDER BY job_id',(user_id,))]
    finally:db.close()

def toggle_saved(user_id, job_id):
    if MONGO_URI:
        # Toggle in one database update to keep the shortlist consistent.
        existing = {'$ifNull': ['$saved_jobs', []]}
        users().update_one({'_id': user_id}, [{'$set': {'saved_jobs': {
            '$cond': [
                {'$in': [job_id, existing]},
                {'$setDifference': [existing, [job_id]]},
                {'$concatArrays': [existing, [job_id]]},
            ]
        }}}])
        return
    db=connect()
    try:
        with db:
            exists=db.execute('SELECT 1 FROM saved_jobs WHERE user_id=? AND job_id=?',(user_id,job_id)).fetchone()
            if exists:db.execute('DELETE FROM saved_jobs WHERE user_id=? AND job_id=?',(user_id,job_id))
            else:db.execute('INSERT INTO saved_jobs(user_id,job_id) VALUES(?,?)',(user_id,job_id))
    finally:db.close()
