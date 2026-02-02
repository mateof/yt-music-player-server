"""Servicio de caché para archivos de audio."""

import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple

# Directorio base para la caché
DATA_DIR = Path(__file__).parent.parent / "data"
CACHE_DIR = DATA_DIR / "_cache"
SETTINGS_FILE = DATA_DIR / "_cache_settings.json"

# Configuración por defecto
DEFAULT_SETTINGS = {
    "retention_days": 10,
    "enabled": True,
}


def _ensure_cache_dir():
    """Asegurar que el directorio de caché existe."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_cache_settings() -> dict:
    """Obtener configuración de caché."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
                # Asegurar que tiene todos los campos
                for key, value in DEFAULT_SETTINGS.items():
                    if key not in settings:
                        settings[key] = value
                return settings
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()


def save_cache_settings(settings: dict) -> dict:
    """Guardar configuración de caché."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Validar y normalizar
    normalized = {
        "retention_days": max(1, min(365, settings.get("retention_days", 10))),
        "enabled": settings.get("enabled", True),
    }

    with open(SETTINGS_FILE, "w") as f:
        json.dump(normalized, f, indent=2)

    return normalized


def get_cached_file(video_id: str) -> Optional[Tuple[bytes, str, str]]:
    """
    Obtener archivo de la caché si existe y no ha expirado.

    Returns:
        Tuple de (audio_data, filename, content_type) o None si no existe
    """
    settings = get_cache_settings()

    if not settings.get("enabled", True):
        return None

    _ensure_cache_dir()

    # Buscar archivo que coincida con el video_id
    for file in CACHE_DIR.iterdir():
        if file.is_file() and file.stem.startswith(video_id):
            # Verificar si no ha expirado
            file_age_days = (time.time() - file.stat().st_mtime) / (24 * 3600)
            retention_days = settings.get("retention_days", 10)

            if file_age_days <= retention_days:
                # Actualizar tiempo de modificación para LRU
                file.touch()

                # Leer archivo
                with open(file, "rb") as f:
                    audio_data = f.read()

                # Determinar content type
                ext = file.suffix.lower()
                content_types = {
                    ".webm": "audio/webm",
                    ".m4a": "audio/mp4",
                    ".mp3": "audio/mpeg",
                    ".opus": "audio/opus",
                    ".ogg": "audio/ogg",
                }
                content_type = content_types.get(ext, "audio/webm")

                print(f"[CACHE] Hit: {file.name}")
                return (audio_data, file.name, content_type)
            else:
                # Archivo expirado, eliminar
                try:
                    file.unlink()
                    print(f"[CACHE] Expired and deleted: {file.name}")
                except Exception:
                    pass

    print(f"[CACHE] Miss: {video_id}")
    return None


def save_to_cache(video_id: str, audio_data: bytes, filename: str, content_type: str) -> bool:
    """
    Guardar archivo en la caché.

    Args:
        video_id: ID del video
        audio_data: Datos del audio
        filename: Nombre del archivo original
        content_type: Tipo MIME del contenido

    Returns:
        True si se guardó correctamente
    """
    settings = get_cache_settings()

    if not settings.get("enabled", True):
        return False

    _ensure_cache_dir()

    # Determinar extensión basada en content type
    extensions = {
        "audio/webm": ".webm",
        "audio/mp4": ".m4a",
        "audio/mpeg": ".mp3",
        "audio/opus": ".opus",
        "audio/ogg": ".ogg",
    }
    ext = extensions.get(content_type, ".webm")

    # Crear nombre de archivo con video_id como prefijo
    cache_filename = f"{video_id}{ext}"
    cache_path = CACHE_DIR / cache_filename

    try:
        with open(cache_path, "wb") as f:
            f.write(audio_data)
        print(f"[CACHE] Saved: {cache_filename} ({len(audio_data)} bytes)")
        return True
    except Exception as e:
        print(f"[CACHE] Error saving: {e}")
        return False


def cleanup_cache() -> dict:
    """
    Limpiar archivos de caché expirados.

    Returns:
        dict con estadísticas de limpieza
    """
    settings = get_cache_settings()
    retention_days = settings.get("retention_days", 10)

    if not CACHE_DIR.exists():
        return {"deleted": 0, "kept": 0, "freed_bytes": 0, "freed_formatted": "0 B"}

    deleted = 0
    kept = 0
    freed_bytes = 0

    for file in CACHE_DIR.iterdir():
        if file.is_file():
            file_age_days = (time.time() - file.stat().st_mtime) / (24 * 3600)

            if file_age_days > retention_days:
                size = file.stat().st_size
                try:
                    file.unlink()
                    deleted += 1
                    freed_bytes += size
                    print(f"[CACHE] Cleanup deleted: {file.name}")
                except Exception:
                    pass
            else:
                kept += 1

    return {
        "deleted": deleted,
        "kept": kept,
        "freed_bytes": freed_bytes,
        "freed_formatted": _format_size(freed_bytes),
    }


def get_cache_stats() -> dict:
    """Obtener estadísticas de la caché."""
    if not CACHE_DIR.exists():
        return {
            "file_count": 0,
            "total_size": 0,
            "total_size_formatted": "0 B",
        }

    file_count = 0
    total_size = 0

    for file in CACHE_DIR.iterdir():
        if file.is_file():
            file_count += 1
            total_size += file.stat().st_size

    return {
        "file_count": file_count,
        "total_size": total_size,
        "total_size_formatted": _format_size(total_size),
    }


def clear_cache() -> dict:
    """Limpiar toda la caché."""
    if not CACHE_DIR.exists():
        return {"deleted": 0, "freed_bytes": 0}

    deleted = 0
    freed_bytes = 0

    for file in CACHE_DIR.iterdir():
        if file.is_file():
            size = file.stat().st_size
            try:
                file.unlink()
                deleted += 1
                freed_bytes += size
            except Exception:
                pass

    return {
        "deleted": deleted,
        "freed_bytes": freed_bytes,
        "freed_formatted": _format_size(freed_bytes),
    }


def _format_size(size_bytes: int) -> str:
    """Formatear tamaño en bytes a formato legible."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
