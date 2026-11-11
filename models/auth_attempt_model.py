"""Small local-demo login throttle, reset by server restart."""
import time
ATTEMPTS={}
WINDOW=300
LIMIT=5

def blocked(key):
    now=time.monotonic()
    for old in list(ATTEMPTS):
        ATTEMPTS[old]=[t for t in ATTEMPTS[old] if now-t<WINDOW]
        if not ATTEMPTS[old]:del ATTEMPTS[old]
    return len(ATTEMPTS.get(key,[]))>=LIMIT

def failed(key):ATTEMPTS.setdefault(key,[]).append(time.monotonic())
def succeeded(key):ATTEMPTS.pop(key,None)
