import io
import os
import re
import tempfile
import yt_dlp


def get_audio_stream_url(video_id: str) -> dict:
    """
    Obtiene la URL directa del stream de audio.
    Más eficiente para streaming ya que evita descargar todo en memoria.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "extractaudio": True,
        # Usar cliente Android/iOS que tiene menos restricciones
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
            }
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        formats = info.get("formats", [])
        audio_formats = [f for f in formats if f.get("acodec") != "none"]

        # Preferir formatos solo audio
        audio_only = [f for f in audio_formats if f.get("vcodec") == "none"]
        if audio_only:
            audio_formats = audio_only

        if not audio_formats:
            raise Exception("No audio format found")

        # Ordenar por calidad
        audio_formats.sort(key=lambda x: x.get("abr", 0) or 0, reverse=True)
        best_audio = audio_formats[0]

        ext = best_audio.get("ext", "webm")
        content_type = "audio/webm"
        if ext == "m4a":
            content_type = "audio/mp4"
        elif ext == "mp3":
            content_type = "audio/mpeg"
        elif ext == "opus":
            content_type = "audio/opus"

        return {
            "url": best_audio.get("url"),
            "contentType": content_type,
            "duration": info.get("duration", 0),
            "title": info.get("title", "Unknown"),
        }


def sanitize_filename(filename: str) -> str:
    """Limpia el nombre de archivo de caracteres no válidos."""
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    if len(filename) > 200:
        filename = filename[:200]
    return filename


def download_audio_file(video_id: str) -> tuple[bytes, str, str]:
    """
    Descarga el audio usando yt-dlp directamente y lo retorna como bytes.
    Retorna: (audio_bytes, filename, content_type)
    """
    url = f"https://www.youtube.com/watch?v={video_id}"

    # Crear directorio temporal
    temp_dir = tempfile.mkdtemp()
    output_template = os.path.join(temp_dir, "%(id)s.%(ext)s")

    # Opciones base
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "outtmpl": output_template,
        # Usar cliente Android/iOS que tiene menos restricciones
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
            }
        },
        # Headers adicionales para evitar bloqueos
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", video_id)
            ext = info.get("ext", "webm")

        # Buscar el archivo descargado
        audio_file = None
        for f in os.listdir(temp_dir):
            if f.startswith(video_id):
                audio_file = os.path.join(temp_dir, f)
                ext = f.split('.')[-1]
                break

        if not audio_file or not os.path.exists(audio_file):
            raise Exception("No se pudo descargar el audio")

        # Determinar content-type
        content_type = "audio/webm"
        if ext == "m4a":
            content_type = "audio/mp4"
        elif ext == "mp3":
            content_type = "audio/mpeg"
        elif ext == "opus":
            content_type = "audio/opus"
        elif ext == "webm":
            content_type = "audio/webm"

        filename = f"{sanitize_filename(title)}.{ext}"

        # Leer el archivo
        with open(audio_file, "rb") as f:
            audio_data = f.read()

        return audio_data, filename, content_type

    finally:
        # Limpiar archivos temporales
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass


def download_as_mp3(video_id: str) -> tuple[str, str]:
    """
    Descarga el audio y lo convierte a MP3 con máxima calidad (320kbps).
    Retorna: (temp_file_path, filename)
    Requiere ffmpeg instalado en el sistema.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"

    # Crear directorio temporal
    temp_dir = tempfile.mkdtemp()
    output_template = os.path.join(temp_dir, "%(title)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "outtmpl": output_template,
        # Usar cliente Android/iOS que tiene menos restricciones
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
            }
        },
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320",  # Máxima calidad
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", video_id)

    # Buscar el archivo MP3 generado
    filename = f"{sanitize_filename(title)}.mp3"
    mp3_path = os.path.join(temp_dir, filename)

    # yt-dlp puede haber usado un nombre ligeramente diferente
    if not os.path.exists(mp3_path):
        # Buscar cualquier archivo .mp3 en el directorio temporal
        for f in os.listdir(temp_dir):
            if f.endswith(".mp3"):
                mp3_path = os.path.join(temp_dir, f)
                filename = f
                break

    if not os.path.exists(mp3_path):
        raise Exception("Failed to convert to MP3. Make sure ffmpeg is installed.")

    return mp3_path, filename
