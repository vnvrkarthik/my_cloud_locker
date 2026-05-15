import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Where the massive files will be saved
UPLOAD_FOLDER = 'cloud_locker_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_chunk():
    """Receives file chunks and stitches them together on the disk."""
    file = request.files['file']
    filename = request.form['filename']
    chunk_index = int(request.form['chunkIndex'])
    total_chunks = int(request.form['totalChunks'])

    save_path = os.path.join(UPLOAD_FOLDER, filename)

    # 'ab' means Append Binary. We just glue the new chunk to the end of the file.
    with open(save_path, 'ab') as f:
        f.write(file.read())

    if chunk_index == total_chunks - 1:
        print(f"✅ Assembly complete: {filename}")
        return jsonify({'status': 'complete'})
    
    return jsonify({'status': 'chunk_received'})

if __name__ == '__main__':
    # threaded=True ensures the server doesn't block while writing to disk
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=True)