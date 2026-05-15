import os
import json
import io
import zipfile
import shutil
from datetime import datetime
from functools import wraps
from flask import Flask, request, render_template, send_from_directory, redirect, url_for, session, flash, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "super_secret_session_key_change_me" 
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100000000 * 1024 * 1024 # 2GB Limit

APP_PASSWORD = "vnvr"
METADATA_FILE = 'metadata.json'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Helper functions
def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_metadata(data):
    with open(METADATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Security check to prevent directory traversal hacks (e.g., ../../)
def get_secure_dir(subpath):
    if not subpath: return app.config['UPLOAD_FOLDER'], ''
    safe_subpath = os.path.normpath(subpath).lstrip('/')
    if '..' in safe_subpath: return app.config['UPLOAD_FOLDER'], ''
    
    target = os.path.join(app.config['UPLOAD_FOLDER'], safe_subpath)
    if os.path.isdir(target): return target, safe_subpath
    return app.config['UPLOAD_FOLDER'], ''

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'): return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.errorhandler(413)
def file_too_large(e):
    flash('Error: The file is too large! Please check your capacity limit.')
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == APP_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            flash('Incorrect password!')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    # Check which folder we are currently looking at
    current_subpath = request.args.get('path', '')
    target_dir, safe_subpath = get_secure_dir(current_subpath)
    metadata = load_metadata()
    
    if request.method == 'POST':
        # Handle New Folder Creation
        if 'new_folder' in request.form:
            folder_name = secure_filename(request.form.get('new_folder'))
            if folder_name:
                os.makedirs(os.path.join(target_dir, folder_name), exist_ok=True)
                flash(f'Folder "{folder_name}" created!')
            return redirect(url_for('index', path=safe_subpath))

        # Handle Drag & Drop Uploads
        if 'files[]' in request.files:
            files = request.files.getlist('files[]')
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            for file in files:
                if file.filename == '': continue
                if file:
                    filename = secure_filename(file.filename)
                    # Save into the CURRENT folder you are viewing
                    file_path = os.path.join(target_dir, filename)
                    file.save(file_path)
                    
                    # Track metadata using the relative path
                    rel_path = f"{safe_subpath}/{filename}".strip('/')
                    metadata[rel_path] = {"upload_time": now, "download_count": 0, "last_download": "Never"}
                    
            save_metadata(metadata)
            return 'Success', 200 # For the JS progress bar
            
    # Read the directory contents
    items = sorted(os.listdir(target_dir))
    folders = [f for f in items if os.path.isdir(os.path.join(target_dir, f))]
    files = [f for f in items if os.path.isfile(os.path.join(target_dir, f))]
    
    # Generate Breadcrumb trails
    parts = safe_subpath.split('/') if safe_subpath else []
    breadcrumbs = []
    accumulated = ""
    for p in parts:
        if p:
            accumulated = f"{accumulated}/{p}" if accumulated else p
            breadcrumbs.append({"name": p, "path": accumulated})

    return render_template('index.html', folders=folders, files=files, current_path=safe_subpath, breadcrumbs=breadcrumbs, metadata=metadata)

@app.route('/download/<path:filepath>')
@login_required
def download_file(filepath):
    safe_path = os.path.normpath(filepath).lstrip('/')
    if '..' in safe_path: return "Invalid Path", 400
    
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_path)
    directory = os.path.dirname(full_path)
    filename = os.path.basename(full_path)
    
    # Update Stats
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
    
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_path)
    directory = os.path.dirname(full_path)
    filename = os.path.basename(full_path)
    return send_from_directory(directory, filename)

@app.route('/delete/<path:filepath>', methods=['POST'])
@login_required
def delete_item(filepath):
    safe_path = os.path.normpath(filepath).lstrip('/')
    if '..' in safe_path: return "Invalid Path", 400
    
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_path)
    
    if os.path.exists(full_path):
        if os.path.isdir(full_path):
            shutil.rmtree(full_path) # Deletes folder and EVERYTHING inside
            flash('Folder deleted.')
        else:
            os.remove(full_path)
            # Remove from metadata
            metadata = load_metadata()
            rel_path = safe_path.replace('\\', '/')
            if rel_path in metadata:
                del metadata[rel_path]
                save_metadata(metadata)
            flash('File deleted.')
            
    # Redirect back to the parent folder
    parent_path = os.path.dirname(safe_path)
    return redirect(url_for('index', path=parent_path))

@app.route('/download_all')
@login_required
def download_all():
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(app.config['UPLOAD_FOLDER']):
            for file in files:
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, app.config['UPLOAD_FOLDER'])
                zf.write(filepath, arcname)
    memory_file.seek(0)
    return send_file(memory_file, download_name='VNVR_Cloud_Backup.zip', as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)




