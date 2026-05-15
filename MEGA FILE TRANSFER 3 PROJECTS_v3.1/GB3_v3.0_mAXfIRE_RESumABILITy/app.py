import os
import aiofiles
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI()

# Bulletproof paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "fast_vault_uploads")
TRACKING_FOLDER = os.path.join(BASE_DIR, "fast_vault_tracking") # NEW: The Ghost Tracker

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TRACKING_FOLDER, exist_ok=True)

@app.get("/")
async def index():
    html_path = os.path.join(TEMPLATE_DIR, "index.html")
    return FileResponse(html_path)

# NEW: The Resume Endpoint
@app.get("/status")
async def check_status(filename: str):
    track_dir = os.path.join(TRACKING_FOLDER, filename)
    if not os.path.exists(track_dir):
        return JSONResponse({"uploaded_chunks": []})
    
    # Read the names of the tiny tracking files to see what's done
    chunks = [int(f) for f in os.listdir(track_dir) if f.isdigit()]
    return JSONResponse({"uploaded_chunks": chunks})

@app.post("/upload")
async def upload_chunk(
    file: UploadFile,
    filename: str = Form(...),
    chunk_index: int = Form(...),
    total_size: int = Form(...),
    chunk_size: int = Form(...)
):
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    track_dir = os.path.join(TRACKING_FOLDER, filename)
    os.makedirs(track_dir, exist_ok=True)
    
    # 1. Allocate the full file instantly (only happens on the first chunk)
    if not os.path.exists(save_path):
        async with aiofiles.open(save_path, 'wb') as f:
            await f.truncate(total_size)
            
    # 2. Inject the data
    offset = chunk_index * chunk_size
    data = await file.read()
    async with aiofiles.open(save_path, 'r+b') as f:
        await f.seek(offset)
        await f.write(data)

    # 3. Drop a Ghost Tracker (an empty file just to prove the chunk finished)
    tracker_file = os.path.join(track_dir, str(chunk_index))
    open(tracker_file, 'w').close()

    return JSONResponse(status_code=200, content={"status": "success"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)