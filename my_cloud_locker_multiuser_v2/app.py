import os
import json
import io
import zipfile
import shutil
from datetime import datetime
from functools import wraps
from flask import Flask, request, render_template, send_from_directory, redirect, url_for, session, flash, send_file
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "super_secret_session_key_change_me" 
app.config['UPLOAD_FOLDER'] = 'uploads'

USERS_FILE = 'users.json'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- USER DATABASE HELPERS ---
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f: return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f: json.dump(users, f, indent=4)

# --- ISOLATED STORAGE HELPERS ---
def get_user_root():
    """Returns the base folder for the currently logged-in user."""
    username = secure_filename(session.get('username'))
    user_dir = os.path.join(app.config['UPLOAD_FOLDER'], username)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def load_metadata():
    meta_file = os.path.join(get_user_root(), 'metadata.json')
    if os.path.exists(meta_file):
        with open(meta_file, 'r') as f: return json.load(f)
    return {}

def save_metadata(data):
    meta_file = os.path.join(get_user_root(), 'metadata.json')
    with open(meta_file, 'w') as f: json.dump(data, f, indent=4)

def get_secure_dir(subpath):
    user_root = get_user_root()
    if not subpath: return user_root, ''
    safe_subpath = os.path.normpath(subpath).lstrip('/')
    if '..' in safe_subpath: return user_root, ''
    
    target = os.path.join(user_root, safe_subpath)
    if os.path.isdir(target): return target, safe_subpath
    return user_root, ''

# --- AUTHENTICATION ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.errorhandler(413)
def file_too_large(e):
    flash('Error: The file is too large!')
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username').lower().strip()
        password = request.form.get('password')
        users = load_users()

        if action == 'register':
            if username in users:
                flash('Error: Username already exists!')
            else:
                users[username] = {'password': generate_password_hash(password)}
                save_users(users)
                flash('Account created successfully! Please log in.')
                
        elif action == 'login':
            if username in users and check_password_hash(users[username]['password'], password):
                session['username'] = username
                return redirect(url_for('index'))
            else:
                flash('Error: Invalid username or password!')
                
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- MAIN APP LOGIC ---
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    current_subpath = request.args.get('path', '')
    target_dir, safe_subpath = get_secure_dir(current_subpath)
    metadata = load_metadata()
    
    if request.method == 'POST':
        if 'new_folder' in request.form:
            folder_name = secure_filename(request.form.get('new_folder'))
            if folder_name:
                os.makedirs(os.path.join(target_dir, folder_name), exist_ok=True)
                flash(f'Folder "{folder_name}" created!')
            return redirect(url_for('index', path=safe_subpath))

        if 'files[]' in request.files:
            files = request.files.getlist('files[]')
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for file in files:
                if file.filename == '': continue
                if file:
                    filename = secure_filename(file.filename)
                    if filename == 'metadata.json': continue # Protect system files
                    file.save(os.path.join(target_dir, filename))
                    
                    rel_path = f"{safe_subpath}/{filename}".strip('/')
                    metadata[rel_path] = {"upload_time": now, "download_count": 0, "last_download": "Never"}
                    
            save_metadata(metadata)
            return 'Success', 200 
            
    items = sorted(os.listdir(target_dir))
    folders = [f for f in items if os.path.isdir(os.path.join(target_dir, f))]
    files = [f for f in items if os.path.isfile(os.path.join(target_dir, f)) and f != 'metadata.json']
    
    parts = safe_subpath.split('/') if safe_subpath else []
    breadcrumbs = []
    accumulated = ""
    for p in parts:
        if p:
            accumulated = f"{accumulated}/{p}" if accumulated else p
            breadcrumbs.append({"name": p, "path": accumulated})

    return render_template('index.html', folders=folders, files=files, current_path=safe_subpath, breadcrumbs=breadcrumbs, metadata=metadata, username=session['username'])

@app.route('/download/<path:filepath>')
@login_required
def download_file(filepath):
    safe_path = os.path.normpath(filepath).lstrip('/')
    if '..' in safe_path: return "Invalid Path", 400
    
    full_path = os.path.join(get_user_root(), safe_path)
    directory = os.path.dirname(full_path)
    filename = os.path.basename(full_path)
    
    metadata = load_metadata()
    rel_path = safe_path.replace('\\', '/')
    if rel_path in metadata:
        metadata[rel_path]['download_count'] += 1
        metadata[rel_path]['last_download'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_metadata(metadata)
        
    return send_from_directory(directory, filename, as_attachment=True)

@app.route('/view/<path:filepath>')
@login_required
def view_file(filepath):
    safe_path = os.path.normpath(filepath).lstrip('/')
    if '..' in safe_path: return "Invalid Path", 400
    
    full_path = os.path.join(get_user_root(), safe_path)
    return send_from_directory(os.path.dirname(full_path), os.path.basename(full_path))

@app.route('/delete/<path:filepath>', methods=['POST'])
@login_required
def delete_item(filepath):
    safe_path = os.path.normpath(filepath).lstrip('/')
    if '..' in safe_path: return "Invalid Path", 400
    full_path = os.path.join(get_user_root(), safe_path)
    
    if os.path.exists(full_path):
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
            flash('Folder deleted.')
        else:
            os.remove(full_path)
            metadata = load_metadata()
            rel_path = safe_path.replace('\\', '/')
            if rel_path in metadata:
                del metadata[rel_path]
                save_metadata(metadata)
            flash('File deleted.')
            
    return redirect(url_for('index', path=os.path.dirname(safe_path)))

@app.route('/download_all')
@login_required
def download_all():
    user_root = get_user_root()
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(user_root):
            for file in files:
                if file == 'metadata.json': continue
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, user_root)
                zf.write(filepath, arcname)
    memory_file.seek(0)
    return send_file(memory_file, download_name=f'{session["username"]}_Cloud_Backup.zip', as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)