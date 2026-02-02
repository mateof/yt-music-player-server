"""Router para podcasts y canales de YouTube Music."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from services.youtube_music import (
    get_library_podcasts_list,
    get_library_channels_list,
    get_channel_info,
    get_channel_episodes_paginated,
    get_podcast_details,
)
from services.auth import is_authenticated

router = APIRouter(prefix="/api/podcasts", tags=["podcasts"])


def _require_auth():
    """Verificar que el usuario está autenticado."""
    if not is_authenticated():
        raise HTTPException(
            status_code=401,
            detail="Se requiere autenticación para acceder a esta función"
        )


@router.get("/library")
async def get_library_podcasts(limit: int = Query(100, ge=1, le=500)):
    """
    Obtener los podcasts suscritos del usuario (Mis Programas).
    Requiere autenticación.
    """
    _require_auth()
    try:
        podcasts = get_library_podcasts_list(limit=limit)
        return {"podcasts": podcasts}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener podcasts: {str(e)}")


@router.get("/channels")
async def get_library_channels(limit: int = Query(100, ge=1, le=500)):
    """
    Obtener los canales suscritos del usuario (Mis Canales).
    Requiere autenticación.
    """
    _require_auth()
    try:
        channels = get_library_channels_list(limit=limit)
        return {"channels": channels}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener canales: {str(e)}")


@router.get("/channel/{channel_id}")
async def get_channel(channel_id: str):
    """
    Obtener información de un canal específico.
    """
    try:
        channel = get_channel_info(channel_id)
        return channel
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener canal: {str(e)}")


@router.get("/channel/{channel_id}/episodes")
async def get_channel_episodes(
    channel_id: str,
    continuation: Optional[str] = Query(None, description="Token de continuación para paginación")
):
    """
    Obtener episodios de un canal con paginación.
    Devuelve una lista de episodios y un token de continuación para la siguiente página.
    """
    try:
        result = get_channel_episodes_paginated(channel_id, continuation)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener episodios: {str(e)}")


@router.get("/podcast/{podcast_id}")
async def get_podcast(podcast_id: str):
    """
    Obtener detalles de un podcast específico.
    """
    try:
        podcast = get_podcast_details(podcast_id)
        return podcast
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener podcast: {str(e)}")
