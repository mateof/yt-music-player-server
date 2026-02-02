"""Router de biblioteca para YouTube Music (requiere autenticación)."""

import os
import re
import asyncio
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from services.youtube_music import (
    get_library_playlists,
    get_liked_songs,
    get_playlist,
    create_playlist,
    add_song_to_playlist,
    delete_playlist,
)
from services.auth import is_authenticated
from services.downloader import download_as_mp3

router = APIRouter(prefix="/api/library", tags=["library"])

# Directorio base para guardar las descargas
DATA_DIR = Path(__file__).parent.parent / "data"


class TrackInfo(BaseModel):
    videoId: str
    title: str


class DownloadPlaylistRequest(BaseModel):
    playlist_name: str
    tracks: List[TrackInfo]


class CreatePlaylistRequest(BaseModel):
    title: str
    description: str = ""
    privacy: str = "PRIVATE"  # PRIVATE, PUBLIC, UNLISTED


class AddSongRequest(BaseModel):
    videoId: str


def _require_auth():
    """Verificar que el usuario está autenticado."""
    if not is_authenticated():
        raise HTTPException(
            status_code=401,
            detail="Se requiere autenticación para acceder a la biblioteca"
        )


@router.get("/playlists")
async def library_playlists(limit: int = Query(500, ge=1, le=1000)):
    """
    Obtener las playlists del usuario.
    Requiere autenticación.
    """
    _require_auth()
    try:
        playlists = get_library_playlists(limit=limit)
        return {"playlists": playlists}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener playlists: {str(e)}")


@router.get("/liked-songs")
async def library_liked_songs(limit: int = Query(5000, ge=1, le=10000)):
    """
    Obtener las canciones que le gustan al usuario.
    Requiere autenticación.
    """
    _require_auth()
    try:
        liked = get_liked_songs(limit=limit)
        return liked
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener canciones: {str(e)}")


@router.get("/playlist/{playlist_id}")
async def library_playlist(playlist_id: str, limit: int = Query(5000, ge=1, le=10000)):
    """
    Obtener detalles de una playlist específica.
    Requiere autenticación para playlists privadas.
    """
    _require_auth()
    try:
        playlist = get_playlist(playlist_id, limit=limit)
        return playlist
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener playlist: {str(e)}")


def _sanitize_folder_name(name: str) -> str:
    """Limpiar el nombre de la carpeta de caracteres no válidos."""
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = name.strip('. ')
    if len(name) > 100:
        name = name[:100]
    return name or "playlist"


def _download_playlist_sync(playlist_name: str, tracks: List[TrackInfo]) -> dict:
    """
    Descarga todas las canciones de una playlist al servidor.
    Esta función se ejecuta en un thread separado.
    """
    # Crear directorio de la playlist
    folder_name = _sanitize_folder_name(playlist_name)
    playlist_dir = DATA_DIR / folder_name
    playlist_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "total": len(tracks),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "errors": [],
        "folder": str(playlist_dir),
    }

    for track in tracks:
        try:
            # Verificar si ya existe el archivo
            existing_files = list(playlist_dir.glob(f"*{track.videoId}*")) + \
                           list(playlist_dir.glob(f"*{_sanitize_folder_name(track.title)}*.mp3"))

            if existing_files:
                print(f"[DOWNLOAD] Saltando (ya existe): {track.title}")
                results["skipped"] += 1
                continue

            print(f"[DOWNLOAD] Descargando: {track.title}")
            mp3_path, filename = download_as_mp3(track.videoId)

            # Mover el archivo al directorio de la playlist
            dest_path = playlist_dir / filename

            # Si ya existe un archivo con ese nombre, agregar un sufijo
            counter = 1
            while dest_path.exists():
                name_without_ext = filename.rsplit('.', 1)[0]
                dest_path = playlist_dir / f"{name_without_ext}_{counter}.mp3"
                counter += 1

            # Mover el archivo
            import shutil
            shutil.move(mp3_path, dest_path)

            # Limpiar directorio temporal
            temp_dir = os.path.dirname(mp3_path)
            if os.path.exists(temp_dir) and os.path.isdir(temp_dir):
                try:
                    os.rmdir(temp_dir)
                except Exception:
                    pass

            print(f"[DOWNLOAD] Guardado: {dest_path}")
            results["success"] += 1

        except Exception as e:
            print(f"[DOWNLOAD] Error descargando {track.title}: {e}")
            results["failed"] += 1
            results["errors"].append({"track": track.title, "error": str(e)})

    return results


@router.post("/download-playlist")
async def download_playlist_to_server(request: DownloadPlaylistRequest):
    """
    Descargar todas las canciones de una playlist al servidor.
    Las guarda en backend/data/{nombre_playlist}/
    """
    _require_auth()

    if not request.tracks:
        raise HTTPException(status_code=400, detail="No hay canciones para descargar")

    try:
        # Ejecutar la descarga en un thread separado para no bloquear
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            _download_playlist_sync,
            request.playlist_name,
            request.tracks
        )

        return {
            "success": True,
            "message": f"Descarga completada: {results['success']} exitosas, {results['skipped']} saltadas, {results['failed']} fallidas",
            "details": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al descargar playlist: {str(e)}")


@router.post("/playlist")
async def create_new_playlist(request: CreatePlaylistRequest):
    """
    Crear una nueva playlist en YouTube Music.
    Requiere autenticación.
    """
    _require_auth()

    if not request.title or len(request.title.strip()) < 1:
        raise HTTPException(status_code=400, detail="El título de la playlist es requerido")

    try:
        result = create_playlist(
            title=request.title.strip(),
            description=request.description,
            privacy=request.privacy
        )
        return {
            "success": True,
            "message": f"Playlist '{request.title}' creada correctamente",
            "playlist": result
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear playlist: {str(e)}")


@router.post("/playlist/{playlist_id}/add")
async def add_song_to_existing_playlist(playlist_id: str, request: AddSongRequest):
    """
    Añadir una canción a una playlist existente.
    Requiere autenticación.
    """
    _require_auth()

    if not request.videoId:
        raise HTTPException(status_code=400, detail="videoId es requerido")

    try:
        result = add_song_to_playlist(playlist_id, request.videoId)
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("message", "Error desconocido"))
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al añadir canción: {str(e)}")


@router.delete("/playlist/{playlist_id}")
async def delete_user_playlist(playlist_id: str):
    """
    Eliminar una playlist de YouTube Music.
    Requiere autenticación.
    """
    _require_auth()

    try:
        result = delete_playlist(playlist_id)
        if result.get("success"):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("message", "Error desconocido"))
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar playlist: {str(e)}")
