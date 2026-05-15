import os
import shutil
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "super_secret_production_key_change_this"  # Needed for secure sessions
APP_PASSWORD = "vnvr"  # CHANGE THIS TO YOUR DESIRED PASSWORD

UPLOAD_FOLDER = 'cloud_locker_uploads'
TEMP_FOLDER = 'cloud_locker_temp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

# --- SECURITY GATES ---
@app.before_request
def check_auth():
    # Force password check for all routes except login and static files
    if request.endpoint not in ['login', 'static'] and not session.get('logged_in'):
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == APP_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        return render_template('index.html', error="Invalid Password", show_login=True)
    return render_template('index.html', show_login=True)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# --- CORE APPLICATION ---
@app.route('/')
def index():
    return render_template('index.html', show_login=False)

@app.route('/status', methods=['GET'])
def check_status():
    """Checks which chunks already exist for resuming interrupted uploads."""
    file_id = request.args.get('file_id')
    temp_dir = os.path.join(TEMP_FOLDER, secure_filename(file_id))
    
    if not os.path.exists(temp_dir):
        return jsonify({'uploaded_chunks': []})
        
    chunks = [int(f.split('_')[1]) for f in os.listdir(temp_dir) if f.startswith('chunk_')]
    return jsonify({'uploaded_chunks': chunks})

@app.route('/upload', methods=['POST'])
def upload_chunk():
    """Receives parallel chunks and saves them in a temporary folder."""
    file = request.files['file']
    file_id = secure_filename(request.form['file_id'])
    chunk_index = request.form['chunkIndex']
    
    temp_dir = os.path.join(TEMP_FOLDER, file_id)
    os.makedirs(temp_dir, exist_ok=True)
    
    chunk_path = os.path.join(temp_dir, f"chunk_{chunk_index}")
    file.save(chunk_path)
    
    return jsonify({'status': 'success'})

@app.route('/assemble', methods=['POST'])
def assemble_file():
    """Stitches all temporary chunks into the final file at maximum disk speed."""
    filename = secure_filename(request.form['filename'])
    file_id = secure_filename(request.form['file_id'])
    total_chunks = int(request.form['totalChunks'])
    
    temp_dir = os.path.join(TEMP_FOLDER, file_id)
    final_path = os.path.join(UPLOAD_FOLDER, filename)
    
    # Check if we actually have all chunks before assembling
    existing_chunks = len([name for name in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, name))])
    if existing_chunks != total_chunks:
        return jsonify({'status': 'error', 'msg': 'Missing chunks'}), 400

    print(f"🔧 Assembling {filename} from {total_chunks} chunks...")
    with open(final_path, 'wb') as final_file:
        for i in range(total_chunks):
            chunk_path = os.path.join(temp_dir, f"chunk_{i}")
            with open(chunk_path, 'rb') as chunk_file:
                shutil.copyfileobj(chunk_file, final_file)
    
    # Clean up temp files
    shutil.rmtree(temp_dir)
    print(f"✅ Assembly complete: {filename}")
    
    return jsonify({'status': 'complete'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=True)