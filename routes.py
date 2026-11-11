"""Route table: URL and method -> controller action."""
from controllers import home_controller as home, resume_controller as resume, job_controller as job, auth_controller as auth
ROUTES={
 ('GET','/login'):auth.login_page, ('POST','/login'):auth.login,
 ('GET','/signup'):auth.signup_page, ('POST','/signup'):auth.signup,
 ('POST','/logout'):auth.logout,
 ('GET','/'):home.home, ('GET','/about'):home.about,
 ('GET','/analyzer'):resume.analyzer, ('POST','/analyze'):resume.analyze,
 ('GET','/jobs'):job.browse, ('GET','/job'):job.detail,
 ('GET','/saved'):job.saved, ('POST','/saved/toggle'):job.toggle,
 ('POST','/skills/clear'):resume.clear_skills,
}
