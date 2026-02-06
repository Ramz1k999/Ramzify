from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import yt_dlp
import os
import hashlib
from typing import List, Optional
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from bot.main import start_bot_polling, bot, dp

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Run bot polling in the background
    asyncio.create_task(start_bot_polling())
    yield
    # Shutdown logic if needed
    await bot.session.close()

app = FastAPI(title="Ramzify", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене укажите конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Директория для хранения файлов
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


class SearchRequest(BaseModel):
    query: str
    max_results: int = 10


class VideoInfo(BaseModel):
    id: str
    title: str
    duration: int
    thumbnail: str
    channel: str
    views: Optional[int] = None


class DownloadRequest(BaseModel):
    video_id: str
    format: str = "mp3"  # mp3 или m4a


@app.get("/")
async def root():
    return {"message": "YouTube Music API", "status": "online"}


@app.post("/search", response_model=List[VideoInfo])
async def search_music(request: SearchRequest):
    """Поиск музыки на YouTube"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'default_search': 'ytsearch',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_query = f"ytsearch{request.max_results}:{request.query}"
            result = ydl.extract_info(search_query, download=False)
            
            if not result or 'entries' not in result:
                return []
            
            videos = []
            for entry in result['entries']:
                if entry:
                    videos.append(VideoInfo(
                        id=entry.get('id', ''),
                        title=entry.get('title', 'Unknown'),
                        duration=entry.get('duration', 0),
                        thumbnail=entry.get('thumbnail', ''),
                        channel=entry.get('channel', 'Unknown'),
                        views=entry.get('view_count')
                    ))
            
            return videos
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/download")
async def download_music(request: DownloadRequest, background_tasks: BackgroundTasks):
    """Скачивание музыки с YouTube"""
    try:
        video_url = f"https://www.youtube.com/watch?v={request.video_id}"
        
        # Генерируем имя файла на основе ID
        file_hash = hashlib.md5(request.video_id.encode()).hexdigest()[:10]
        output_filename = f"{file_hash}.{request.format}"
        output_path = DOWNLOAD_DIR / output_filename
        
        # Если файл уже существует, возвращаем его
        if output_path.exists():
            return {
                "status": "ready",
                "filename": output_filename,
                "download_url": f"/download/file/{output_filename}"
            }
        
        # Настройки для скачивания
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': request.format,
                'preferredquality': '192',
            }],
            'outtmpl': str(DOWNLOAD_DIR / file_hash),
            'quiet': True,
            'no_warnings': True,
        }
        
        # Скачиваем асинхронно
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        # Планируем удаление файла через 1 час
        background_tasks.add_task(cleanup_file, output_path, delay=3600)
        
        return {
            "status": "ready",
            "filename": output_filename,
            "download_url": f"/download/file/{output_filename}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/file/{filename}")
async def get_file(filename: str):
    """Получить скачанный файл"""
    file_path = DOWNLOAD_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        media_type="audio/mpeg",
        filename=filename
    )


@app.get("/info/{video_id}")
async def get_video_info(video_id: str):
    """Получить детальную информацию о видео"""
    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            return {
                "id": info.get('id'),
                "title": info.get('title'),
                "duration": info.get('duration'),
                "thumbnail": info.get('thumbnail'),
                "channel": info.get('channel'),
                "views": info.get('view_count'),
                "description": info.get('description', '')[:200] + '...',
                "upload_date": info.get('upload_date'),
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def cleanup_file(file_path: Path, delay: int):
    """Удалить файл через указанное время"""
    await asyncio.sleep(delay)
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
