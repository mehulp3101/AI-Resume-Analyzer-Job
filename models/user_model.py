"""User validation, persistence and password verification. No HTML/HTTP."""
import hashlib
import hmac
import re
import secrets
import sqlite3
from models.database import connect
from models.mongo_database import MONGO_URI, users
ITERATIONS = 600000

def normalize_email(value):
    return value.strip().lower()

def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), ITERATIONS)
    return f'pbkdf2_sha256${ITERATIONS}${salt}${digest.hex()}'

def verify_password(password, stored):
    try:
        algorithm, iterations, salt, digest = stored.split('$')
        if algorithm != 'pbkdf2_sha256': return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(actual.hex(), digest)
    except (ValueError, TypeError):
        return False

# Use the same expensive verification path for unknown email addresses.
DUMMY_HASH = hash_password('not-a-real-account-password')

def create_user(name, email, password, confirmation):
    name = name.strip()
    email = normalize_email(email)
    if not 2 <= len(name) <= 80:
        raise ValueError('Enter a name between 2 and 80 characters.')
    if len(email)>254 or not re.fullmatch(r'[a-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}', email):
        raise ValueError('Enter a valid email address.')
    if not 10 <= len(password) <= 128:
        raise ValueError('Use a password between 10 and 128 characters.')
    if password != confirmation:
        raise ValueError('The passwords do not match.')
    encoded = hash_password(password)
    if MONGO_URI:
        from pymongo.errors import DuplicateKeyError
        try:
            result = users().insert_one({
                'name': name, 'email': email, 'password_hash': encoded, 'saved_jobs': [],
            })
        except DuplicateKeyError:
            raise ValueError('This email is already registered. Please log in.') from None
        return {'id': result.inserted_id, 'name': name, 'email': email}
    db = connect()
    try:
        with db:
            cursor = db.execute('INSERT INTO users(name,email,password_hash) VALUES(?,?,?)', (name,email,encoded))
        return {'id':cursor.lastrowid,'name':name,'email':email}
    except sqlite3.IntegrityError:
        raise ValueError('This email is already registered. Please log in.') from None
    finally:
        db.close()

def authenticate(email, password):
    if MONGO_URI:
        row = users().find_one({'email': normalize_email(email)})
        if row:
            row['id'] = row['_id']
    else:
        db=connect()
        try: row=db.execute('SELECT * FROM users WHERE email=?',(normalize_email(email),)).fetchone()
        finally: db.close()
    candidate = password if len(password)<=128 else ''
    valid=verify_password(candidate,row['password_hash'] if row else DUMMY_HASH)
    return {'id':row['id'],'name':row['name'],'email':row['email']} if row and valid else None

def get_user(user_id):
    if MONGO_URI:
        row = users().find_one({'_id': user_id}, {'name': 1, 'email': 1})
        return {'id': row['_id'], 'name': row['name'], 'email': row['email']} if row else None
    db=connect()
    try:
        row=db.execute('SELECT id,name,email FROM users WHERE id=?',(user_id,)).fetchone()
        return dict(row) if row else None
    finally: db.close()
