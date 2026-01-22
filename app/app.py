from fastapi import FastAPI, Request, BackgroundTasks, Form, File, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl
from typing import Optional
import asyncio
import concurrent.futures
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

class UrlRequest(BaseModel):
    url: HttpUrl
    lang: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    external_api_url = os.getenv("EXTERNAL_API_URL", "")
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "external_api_url": external_api_url
    })

# http://ser_downvideo:5000/subtitles?url=https://www.youtube.com/watch?v=byYlC2cagLw
@app.get("/subtitles")
async def subtitle(url: str, background_tasks: BackgroundTasks, lang: Optional[str] = None):
    task_id = get_next_task_id()
    task_storage[task_id] = {"status": "processing", "result": None, "error": None}
    
    def process_subtitle():
        try:
            print(f" download_sub({url}, {lang}, {task_id})")
            result = download_sub(url, lang, task_id)
            task_storage[task_id] = {"status": "completed", "result": result, "error": None}
        except Exception as e:
            task_storage[task_id] = {"status": "error", "result": None, "error": str(e)}
    
    background_tasks.add_task(process_subtitle)
    return {"task_id": task_id, "status": "processing", "message": "Task started in background"}

@app.get("/title")
async def title(url: str, background_tasks: BackgroundTasks):
    task_id = get_next_task_id()
    task_storage[task_id] = {"status": "processing", "result": None, "error": None}
    
    def process_title():
        try:
            result = obtener_titulo_video_youtube(url)
            task_storage[task_id] = {"status": "completed", "result": result, "error": None}
        except Exception as e:
            task_storage[task_id] = {"status": "error", "result": None, "error": str(e)}
    
    background_tasks.add_task(process_title)
    return {"task_id": task_id, "status": "processing", "message": "Task started in background"}

@app.get("/audio")
async def downaudio(url: str, background_tasks: BackgroundTasks):
    task_id = get_next_task_id()
    task_storage[task_id] = {"status": "processing", "result": None, "error": None}
    
    def process_audio():
        try:
            result = download_audio(url, task_id)
            task_storage[task_id] = {"status": "completed", "result": result, "error": None}
        except Exception as e:
            task_storage[task_id] = {"status": "error", "result": None, "error": str(e)}
    
    background_tasks.add_task(process_audio)
    return {"task_id": task_id, "status": "processing", "message": "Task started in background"}

@app.get("/video")
async def downvideo(url: str, background_tasks: BackgroundTasks):
    task_id = get_next_task_id()
    task_storage[task_id] = {"status": "processing", "result": None, "error": None}
    
    def process_video():
        try:
            print(url)
            result = download_video(url, task_id)
            task_storage[task_id] = {"status": "completed", "result": result, "error": None}
        except Exception as e:
            task_storage[task_id] = {"status": "error", "result": None, "error": str(e)}
    
    background_tasks.add_task(process_video)
    return {"task_id": task_id, "status": "processing", "message": "Task started in background"}

@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in task_storage:
        return JSONResponse(content={"error": "Task not found"}, status_code=404)
    
    return JSONResponse(content=task_storage[task_id])

@app.get("/tasks")
async def get_all_tasks():
    return JSONResponse(content=task_storage)

# New endpoints for the web interface
@app.get("/process-audio")
async def process_audio(url: str, background_tasks: BackgroundTasks):
    """Endpoint to start audio download process"""
    task_id = get_next_task_id()
    task_storage[task_id] = {"status": "processing", "result": None, "error": None}
    
    def process_audio_task():
        try:
            result = download_audio(url, task_id)
            task_storage[task_id] = {"status": "completed", "result": result, "error": None}
        except Exception as e:
            task_storage[task_id] = {"status": "error", "result": None, "error": str(e)}
    
    background_tasks.add_task(process_audio_task)
    return {"task_id": task_id, "status": "processing", "message": "Audio download started in background"}

@app.get("/get-audio-file/{filename}")
async def get_audio_file(filename: str):
    """Endpoint to download the generated audio file"""
    file_path = os.path.join("/resources/audios/", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='audio/mpeg', filename=filename)
    else:
        return JSONResponse(content={"error": "File not found"}, status_code=404)

@app.post("/send-external")
async def send_external(
    title: str = Form(...),
    url: str = Form(...),
    filename: str = Form(...),
    file: UploadFile = File(...)
):
    """Endpoint to send data to external service"""
    try:
        # Get external API URL from environment variable
        external_api_url = os.getenv("EXTERNAL_API_URL", "")
        
        # Prepare the multipart form data for the external service
        files = {
            'title': (None, title),
            'url': (None, url), 
            'filename': (None, filename),
            'audio_file': (filename, await file.read(), file.content_type)
        }
        
        # Send POST request to external service
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{external_api_url}/external_link',
                files=files,
                headers={'accept': 'application/json'},
                timeout=30.0
            )
            
        if response.status_code == 200:
            return {"status": "success", "message": "Data sent successfully", "response": response.json()}
        else:
            return JSONResponse(
                content={"error": f"External service returned status {response.status_code}", "details": response.text},
                status_code=response.status_code
            )
            
    except Exception as e:
        return JSONResponse(
            content={"error": f"Failed to send data to external service: {str(e)}"},
            status_code=500
        )

@app.get("/auto-audio", response_class=HTMLResponse)
async def auto_audio(request: Request, url: str, background_tasks: BackgroundTasks):
    """Endpoint to automatically download audio and upload to external service (returns HTML status page)"""
    task_id = get_next_task_id()
    task_storage[task_id] = {"status": "processing", "result": None, "error": None}
    
    async def process_and_upload():
        try:
            # Validate external API URL is configured
            external_api_url = os.getenv("EXTERNAL_API_URL", "").strip()
            if not external_api_url:
                raise ValueError("EXTERNAL_API_URL is not configured in environment variables")
            
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
                            "error": None
                        }
                    else:
                        error_msg = f"External service returned status {response.status_code}: {response.text}"
                        print(f"[{task_id}] Error: {error_msg}")
                        task_storage[task_id] = {
                            "status": "error", 
                            "result": None, 
                            "error": error_msg
                        }
        except Exception as e:
            error_msg = str(e)
            print(f"[{task_id}] Exception: {error_msg}")
            task_storage[task_id] = {"status": "error", "result": None, "error": error_msg}
    
    background_tasks.add_task(process_and_upload)
    
    # Return HTML page showing the status
    return templates.TemplateResponse("auto_audio.html", {
        "request": request,
        "task_id": task_id,
        "url": url
    })
