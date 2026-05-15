import os
import aiofiles
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI()

# Bulletproof paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "fast_vault_uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.get("/")
async def index():
    # FileResponse just sends the file exactly as it is. No processing, no crashing.
    html_path = os.path.join(TEMPLATE_DIR, "index.html")
    return FileResponse(html_path)

@app.post("/upload")
async def upload_chunk(
    file: UploadFile,
    filename: str = Form(...),
    chunk_index: int = Form(...),
    total_size: int = Form(...),
    chunk_size: int = Form(...)
):
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    
    # 1. Allocate the full 3GB file instantly on disk
    if not os.path.exists(save_path):
        async with aiofiles.open(save_path, 'wb') as f:
            await f.truncate(total_size)
            
    # 2. Calculate offset
    offset = chunk_index * chunk_size
    
    # 3. Read and inject chunk data
    data = await file.read()
    async with aiofiles.open(save_path, 'r+b') as f:
        await f.seek(offset)
        await f.write(data)

    return JSONResponse(status_code=200, content={"status": "success"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)