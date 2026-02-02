import asyncio
import os
import re
import httpx
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse, StreamingResponse, FileResponse

from services.downloader import get_audio_stream_url, download_as_mp3, download_audio_file
from services.cache import get_cached_file, save_to_cache

router = APIRouter(prefix="/api", tags=["stream"])


def sanitize_filename(filename: str) -> str:
    """Limpia el nombre de archivo de caracteres no válidos."""
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    if len(filename) > 200:
        filename = filename[:200]
    return filename


@router.get("/stream/{video_id}")
async def stream_audio(video_id: str):
    """
    Descarga el audio usando yt-dlp y lo envía al cliente.
    Usa caché para evitar descargas repetidas.
    """
    try:
        # Primero buscar en caché
        cached = get_cached_file(video_id)

        if cached:
            audio_data, filename, content_type = cached
            print(f"[STREAM] Sirviendo desde caché: {len(audio_data)} bytes")
        else:
            # Ejecutar la descarga en un thread separado para no bloquear
            loop = asyncio.get_event_loop()
            audio_data, filename, content_type = await loop.run_in_executor(
                None, download_audio_file, video_id
            )

            print(f"[STREAM] Audio descargado: {len(audio_data)} bytes, tipo: {content_type}")

            # Guardar en caché en background
            loop.run_in_executor(None, save_to_cache, video_id, audio_data, filename, content_type)

        # Crear un generador para enviar los datos en chunks
        async def audio_stream():
            chunk_size = 65536
            for i in range(0, len(audio_data), chunk_size):
                yield audio_data[i:i + chunk_size]

        return StreamingResponse(
            audio_stream(),
            media_type=content_type,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(len(audio_data)),
                "Cache-Control": "no-cache",
            }
        )
    except Exception as e:
        print(f"[STREAM] Exception: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream-info/{video_id}")
async def get_stream_info(video_id: str):
    """
    Obtiene información del stream sin redirigir.
    """
    try:
        stream_info = get_audio_stream_url(video_id)
        return stream_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{video_id}")
async def download_audio(video_id: str, background_tasks: BackgroundTasks):
    """
    Descarga el audio, lo convierte a MP3 (320kbps) y lo envía como archivo descargable.
    Requiere ffmpeg instalado en el sistema.
    """
    try:
        # Descargar y convertir a MP3
        mp3_path, filename = download_as_mp3(video_id)

        # Programar limpieza del archivo temporal después de enviar
        def cleanup():
            try:
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
                # Eliminar directorio temporal
                temp_dir = os.path.dirname(mp3_path)
                if os.path.exists(temp_dir) and os.path.isdir(temp_dir):
                    os.rmdir(temp_dir)
            except Exception:
                pass

        background_tasks.add_task(cleanup)

        return FileResponse(
            path=mp3_path,
            media_type="audio/mpeg",
            filename=filename,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download-info/{video_id}")
async def get_download_info(video_id: str):
    """
    Obtiene la URL directa para descargar.
    """
    try:
        stream_info = get_audio_stream_url(video_id)
        return {
            "url": stream_info["url"],
            "title": stream_info["title"],
            "contentType": stream_info["contentType"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
