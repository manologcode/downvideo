from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Optional
import httpx
import os

from ytdlp import *

app = FastAPI()

# Configure templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Dictionary to store task status and results
task_storage = {}
task_counter = 0

def get_next_task_id():
    global task_counter
    task_counter += 1
    return f"task_{task_counter}"

async def upload_to_external_service(task_id: str, title: str, url: str, filename: str, file_path: str, auto_upload: bool):
    """Upload audio file to external service if enabled"""
    if not auto_upload:
        # Auto-upload disabled, just mark as completed
        print(f"[{task_id}] Auto-upload disabled. Audio ready for download/manual upload")
        task_storage[task_id] = {
            "status": "completed", 
            "result": {"message": "Audio downloaded successfully", "filename": filename, "title": title}, 
            "error": None,
            "autoUpload": auto_upload
        }
        return
    
    # Auto-upload enabled, validate and upload
    external_api_url = os.getenv("EXTERNAL_API_URL", "").strip()
    if not external_api_url:
        raise ValueError("EXTERNAL_API_URL is not configured in environment variables")
    
    print(f"[{task_id}] Uploading to external API: {external_api_url}")
    
    # Upload to external service
    with open(file_path, 'rb') as f:
        files = {
            'title': (None, title),
            'url': (None, url), 
            'filename': (None, filename),
            'audio_file': (filename, f, 'audio/mpeg')
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                external_api_url,
                files=files,
                headers={'accept': 'application/json'},
                timeout=30.0
            )
            
            print(f"[{task_id}] External API response: {response.status_code}")
            
            if response.status_code == 200:
                print(f"[{task_id}] Successfully uploaded to external API")
                task_storage[task_id] = {
                    "status": "completed", 
                    "result": {"message": "Audio downloaded and uploaded successfully", "filename": filename, "title": title}, 
                    "error": None,
                    "autoUpload": auto_upload
                }
            else:
                error_msg = f"External service returned status {response.status_code}: {response.text}"
                print(f"[{task_id}] Error: {error_msg}")
                task_storage[task_id] = {
                    "status": "error", 
                    "result": None, 
                    "error": error_msg,
                    "autoUpload": auto_upload
                }

@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in task_storage:
        return JSONResponse(content={"error": "Task not found"}, status_code=404)
    
    return JSONResponse(content=task_storage[task_id])

@app.get("/get-audio-file/{filename}")
async def get_audio_file(filename: str):
    """Endpoint to download the generated audio file"""
    file_path = os.path.join("/resources/audios/", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='audio/mpeg', filename=filename)
    else:
        return JSONResponse(content={"error": "File not found"}, status_code=404)

@app.get("/", response_class=HTMLResponse)
async def auto_audio(request: Request, url: Optional[str] = None, autoUpload: Optional[str] = None, background_tasks: BackgroundTasks = None):
    """Root endpoint to download audio and optionally upload to external service"""
    
    # If url is not provided, show form to input it
    if not url:
        return templates.TemplateResponse("auto_audio_form.html", {
            "request": request
        })
    
    # Convert autoUpload string to boolean (default is True)
    auto_upload = autoUpload != "false" if autoUpload else True
    
    # Create task
    task_id = get_next_task_id()
    task_storage[task_id] = {"status": "processing", "result": None, "error": None, "autoUpload": auto_upload}
    
    async def process_audio_task():
        try:
            print(f"[{task_id}] Starting audio download for: {url}")
            
            # Download audio
            audio_result = download_audio(url, task_id)
            title = audio_result['title']
            filename = audio_result['file_name']
            file_path = os.path.join("/resources/audios/", filename)
            
            print(f"[{task_id}] Audio downloaded to: {file_path}")
            
            # Verify file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Audio file not found at {file_path}")
            
            # Upload to external service if enabled
            await upload_to_external_service(task_id, title, url, filename, file_path, auto_upload)
            
        except Exception as e:
            error_msg = str(e)
            print(f"[{task_id}] Exception: {error_msg}")
            task_storage[task_id] = {"status": "error", "result": None, "error": error_msg, "autoUpload": auto_upload}
    
    background_tasks.add_task(process_audio_task)
    
    # Get external API URL
    external_api_url = os.getenv("EXTERNAL_API_URL", "")
    
    # Return HTML page showing the status
    return templates.TemplateResponse("auto_audio.html", {
        "request": request,
        "task_id": task_id,
        "url": url,
        "external_api_url": external_api_url
    })
