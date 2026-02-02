"""Router para gestión de archivos locales descargados."""

import os
import zipfile
import io
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/local", tags=["local"])

# Directorio base donde están las descargas
DATA_DIR = Path(__file__).parent.parent / "data"


class LocalTrack(BaseModel):
    filename: str
    title: str
    size: int
    path: str


class LocalPlaylist(BaseModel):
    name: str
    folder: str
    trackCount: int
    totalSize: int


class LocalPlaylistDetail(BaseModel):
    name: str
    folder: str
    tracks: List[LocalTrack]
    totalSize: int


def _get_file_size_mb(size_bytes: int) -> str:
    """Convertir bytes a formato legible."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


@router.get("/playlists")
async def list_local_playlists() -> dict:
    """
    Listar todas las playlists descargadas localmente.
    """
    if not DATA_DIR.exists():
        return {"playlists": []}

    playlists = []
    for folder in DATA_DIR.iterdir():
        if folder.is_dir():
            # Contar archivos de audio
            audio_files = list(folder.glob("*.mp3")) + list(folder.glob("*.m4a")) + \
                         list(folder.glob("*.webm")) + list(folder.glob("*.opus"))

            total_size = sum(f.stat().st_size for f in audio_files)

            playlists.append({
                "name": folder.name,
                "folder": str(folder),
                "trackCount": len(audio_files),
                "totalSize": total_size,
                "totalSizeFormatted": _get_file_size_mb(total_size),
            })

    # Ordenar por nombre
    playlists.sort(key=lambda x: x["name"].lower())

    return {"playlists": playlists}


@router.get("/playlist/{playlist_name}")
async def get_local_playlist(playlist_name: str) -> dict:
    """
    Obtener detalles de una playlist local.
    """
    playlist_dir = DATA_DIR / playlist_name

    if not playlist_dir.exists() or not playlist_dir.is_dir():
        raise HTTPException(status_code=404, detail="Playlist no encontrada")

    # Listar archivos de audio
    audio_extensions = (".mp3", ".m4a", ".webm", ".opus", ".ogg", ".wav")
    tracks = []
    total_size = 0

    for file in sorted(playlist_dir.iterdir()):
        if file.is_file() and file.suffix.lower() in audio_extensions:
            size = file.stat().st_size
            total_size += size

            # Extraer título del nombre de archivo (sin extensión)
            title = file.stem

            tracks.append({
                "filename": file.name,
                "title": title,
                "size": size,
                "sizeFormatted": _get_file_size_mb(size),
                "path": str(file),
                "extension": file.suffix.lower(),
            })

    return {
        "name": playlist_name,
        "folder": str(playlist_dir),
        "tracks": tracks,
        "trackCount": len(tracks),
        "totalSize": total_size,
        "totalSizeFormatted": _get_file_size_mb(total_size),
    }


@router.get("/stream/{playlist_name}/{filename}")
async def stream_local_file(playlist_name: str, filename: str):
    """
    Reproducir un archivo de audio local.
    """
    file_path = DATA_DIR / playlist_name / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    # Determinar content type
    extension = file_path.suffix.lower()
    content_types = {
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".webm": "audio/webm",
        ".opus": "audio/opus",
        ".ogg": "audio/ogg",
        ".wav": "audio/wav",
    }
    content_type = content_types.get(extension, "audio/mpeg")

    return FileResponse(
        path=file_path,
        media_type=content_type,
        filename=filename,
    )


@router.get("/download/{playlist_name}/{filename}")
async def download_local_file(playlist_name: str, filename: str):
    """
    Descargar un archivo de audio individual.
    """
    file_path = DATA_DIR / playlist_name / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/download-zip/{playlist_name}")
async def download_playlist_zip(playlist_name: str):
    """
    Descargar toda la playlist como archivo ZIP.
    """
    playlist_dir = DATA_DIR / playlist_name

    if not playlist_dir.exists() or not playlist_dir.is_dir():
        raise HTTPException(status_code=404, detail="Playlist no encontrada")

    # Crear ZIP en memoria
    zip_buffer = io.BytesIO()

    audio_extensions = (".mp3", ".m4a", ".webm", ".opus", ".ogg", ".wav")

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file in playlist_dir.iterdir():
            if file.is_file() and file.suffix.lower() in audio_extensions:
                zip_file.write(file, file.name)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{playlist_name}.zip"'
        }
    )


@router.delete("/playlist/{playlist_name}")
async def delete_local_playlist(playlist_name: str):
    """
    Eliminar una playlist local y todos sus archivos.
    """
    playlist_dir = DATA_DIR / playlist_name

    if not playlist_dir.exists() or not playlist_dir.is_dir():
        raise HTTPException(status_code=404, detail="Playlist no encontrada")

    import shutil
    try:
        shutil.rmtree(playlist_dir)
        return {"success": True, "message": f"Playlist '{playlist_name}' eliminada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar: {str(e)}")


@router.delete("/playlist/{playlist_name}/{filename}")
async def delete_local_file(playlist_name: str, filename: str):
    """
    Eliminar un archivo de audio individual.
    """
    file_path = DATA_DIR / playlist_name / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    try:
        file_path.unlink()
        return {"success": True, "message": f"Archivo '{filename}' eliminado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar: {str(e)}")
