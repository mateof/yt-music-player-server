from fastapi import APIRouter, Query, HTTPException

from services.youtube_music import (
    search_songs,
    search_by_genre,
    search_podcasts,
    search_episodes,
    get_podcast_details,
    get_home,
)

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search")
async def search(
    q: str = Query(..., min_length=1, description="Término de búsqueda"),
    type: str = Query("songs", description="Tipo: songs, podcasts, episodes"),
):
    """Buscar por término. Tipo puede ser: songs, podcasts, episodes."""
    try:
        if type == "podcasts":
            results = search_podcasts(q)
        elif type == "episodes":
            results = search_episodes(q)
        else:
            results = search_songs(q)
        return {"results": results, "query": q, "type": type}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/genre/{genre}")
async def search_genre(genre: str):
    """Buscar canciones por género."""
    try:
        results = search_by_genre(genre)
        return {"results": results, "genre": genre}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/podcasts")
async def podcasts(q: str = Query(..., min_length=1, description="Término de búsqueda")):
    """Buscar podcasts por término."""
    try:
        results = search_podcasts(q)
        return {"results": results, "query": q}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/podcast/{podcast_id}")
async def podcast_detail(podcast_id: str):
    """Obtener detalles de un podcast y sus episodios ordenados por fecha descendente."""
    try:
        podcast = get_podcast_details(podcast_id)
        return podcast
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episodes")
async def episodes(q: str = Query(..., min_length=1, description="Término de búsqueda")):
    """Buscar episodios de podcast por término."""
    try:
        results = search_episodes(q)
        return {"results": results, "query": q}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/home")
async def home():
    """Obtener recomendaciones y contenido popular."""
    try:
        results = get_home()
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
