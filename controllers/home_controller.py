from views.renderer import page
def home(session, query, form):
    return 200, page('home.html', 'Home', '/', session)
def about(session, query, form):
    return 200, page('about.html', 'About', '/about', session)
