from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import search, stream, auth, library, local, podcasts, cache
from services.cache import cleanup_cache
from version import __version__, __app_name__


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación."""
    # Al iniciar: limpiar caché expirada
    print("[STARTUP] Limpiando caché expirada...")
    result = cleanup_cache()
    print(f"[STARTUP] Caché limpiada: {result['deleted']} archivos eliminados, {result['freed_formatted']} liberados")
    yield
    # Al cerrar: nada por ahora


app = FastAPI(
    title=__app_name__,
    description="API para buscar y reproducir música de YouTube",
    version=__version__,
    lifespan=lifespan,
)

# Configurar CORS - permitir todos los orígenes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# Incluir routers
app.include_router(search.router)
app.include_router(stream.router)
app.include_router(auth.router)
app.include_router(library.router)
app.include_router(local.router)
app.include_router(podcasts.router)
app.include_router(cache.router)


@app.get("/")
async def root():
    return {
        "message": __app_name__,
        "version": __version__,
        "docs": "/docs",
        "endpoints": {
            "search": "/api/search?q=query",
            "genre": "/api/search/genre/{genre}",
            "home": "/api/home",
            "stream": "/api/stream/{video_id}",
            "download": "/api/download/{video_id}",
            "auth_status": "/api/auth/status",
            "auth_login": "/api/auth/login",
            "auth_logout": "/api/auth/logout",
            "library_playlists": "/api/library/playlists",
            "library_liked_songs": "/api/library/liked-songs",
            "library_playlist": "/api/library/playlist/{playlist_id}",
            "podcasts_library": "/api/podcasts/library",
            "podcasts_channels": "/api/podcasts/channels",
            "podcasts_channel": "/api/podcasts/channel/{channel_id}",
            "podcasts_channel_episodes": "/api/podcasts/channel/{channel_id}/episodes",
            "local_playlists": "/api/local/playlists",
            "local_playlist": "/api/local/playlist/{name}",
            "local_stream": "/api/local/stream/{playlist}/{filename}",
            "local_download": "/api/local/download/{playlist}/{filename}",
            "local_download_zip": "/api/local/download-zip/{playlist}",
            "cache_settings": "/api/cache/settings",
            "cache_stats": "/api/cache/stats",
            "cache_cleanup": "/api/cache/cleanup",
            "cache_clear": "/api/cache/clear",
        },
    }
