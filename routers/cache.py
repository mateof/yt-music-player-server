"""Router para gestión de caché de audio."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.cache import (
    get_cache_settings,
    save_cache_settings,
    get_cache_stats,
    cleanup_cache,
    clear_cache,
)

router = APIRouter(prefix="/api/cache", tags=["cache"])


class CacheSettingsRequest(BaseModel):
    retention_days: int = 10
    enabled: bool = True


@router.get("/settings")
async def get_settings():
    """Obtener configuración de caché."""
    try:
        settings = get_cache_settings()
        return settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings")
async def update_settings(request: CacheSettingsRequest):
    """Actualizar configuración de caché."""
    try:
        settings = save_cache_settings({
            "retention_days": request.retention_days,
            "enabled": request.enabled,
        })
        return {
            "success": True,
            "settings": settings,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """Obtener estadísticas de la caché."""
    try:
        stats = get_cache_stats()
        settings = get_cache_settings()
        return {
            **stats,
            "settings": settings,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def run_cleanup():
    """Ejecutar limpieza de archivos expirados."""
    try:
        result = cleanup_cache()
        return {
            "success": True,
            "message": f"Limpieza completada: {result['deleted']} archivos eliminados",
            **result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def run_clear():
    """Limpiar toda la caché."""
    try:
        result = clear_cache()
        return {
            "success": True,
            "message": f"Caché limpiada: {result['deleted']} archivos eliminados",
            **result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
