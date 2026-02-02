from ytmusicapi import YTMusic
from services.auth import get_authenticated_ytmusic, is_authenticated

# Instancia sin autenticar (siempre disponible)
_ytmusic_public = YTMusic()


def _get_ytmusic(require_auth: bool = False) -> YTMusic | None:
    """
    Obtener instancia de YTMusic.

    Args:
        require_auth: Si True, retorna None si no hay autenticación

    Returns:
        Instancia de YTMusic autenticada si está disponible, o pública si no
    """
    if require_auth:
        return get_authenticated_ytmusic()

    # Preferir instancia autenticada si existe
    auth_ytmusic = get_authenticated_ytmusic()
    return auth_ytmusic if auth_ytmusic else _ytmusic_public


# Para compatibilidad, mantener referencia pública
ytmusic = _ytmusic_public


def search_songs(query: str, limit: int = 20) -> list[dict]:
    """Buscar canciones por término."""
    yt = _get_ytmusic()
    results = yt.search(query, filter="songs", limit=limit)
    return [_format_song(song) for song in results]


def search_by_genre(genre: str, limit: int = 20) -> list[dict]:
    """Buscar canciones por género."""
    yt = _get_ytmusic()
    results = yt.search(f"{genre} music", filter="songs", limit=limit)
    return [_format_song(song) for song in results]


def search_podcasts(query: str, limit: int = 20) -> list[dict]:
    """Buscar podcasts por término."""
    yt = _get_ytmusic()
    results = yt.search(query, filter="podcasts", limit=limit)
    return [_format_podcast(podcast) for podcast in results]


def search_episodes(query: str, limit: int = 20) -> list[dict]:
    """Buscar episodios de podcast por término."""
    yt = _get_ytmusic()
    results = yt.search(query, filter="episodes", limit=limit)
    return [_format_episode(episode) for episode in results]


def get_podcast_details(podcast_id: str) -> dict:
    """Obtener detalles de un podcast y sus episodios."""
    yt = _get_ytmusic()

    # If the ID starts with UC, it's a channel ID - try to get channel info instead
    if podcast_id.startswith("UC"):
        try:
            return _get_channel_as_podcast(yt, podcast_id)
        except Exception:
            pass  # Fall through to try get_podcast

    try:
        podcast = yt.get_podcast(podcast_id)
    except Exception as e:
        # If get_podcast fails and it looks like a channel ID, try channel approach
        if "UC" in podcast_id:
            return _get_channel_as_podcast(yt, podcast_id)
        raise e

    # Información del podcast
    author = podcast.get("author", {})
    author_name = author.get("name", "Unknown") if isinstance(author, dict) else str(author) if author else "Unknown"

    thumbnails = podcast.get("thumbnails", [])
    thumbnail = thumbnails[-1]["url"] if thumbnails else None

    # Episodios (ya vienen ordenados por fecha descendente desde la API)
    episodes = []
    for ep in podcast.get("episodes", []):
        episodes.append(_format_podcast_episode(ep, podcast.get("title", "Unknown Podcast")))

    return {
        "podcastId": podcast_id,
        "title": podcast.get("title", "Unknown Podcast"),
        "author": author_name,
        "description": podcast.get("description", ""),
        "thumbnail": thumbnail,
        "episodes": episodes,
        "type": "podcast",
    }


def _get_channel_as_podcast(yt, channel_id: str) -> dict:
    """Get channel info formatted as podcast response."""
    channel = yt.get_channel(channel_id)

    thumbnails = channel.get("thumbnails", [])
    thumbnail = thumbnails[-1]["url"] if thumbnails else None

    # Get episodes from channel
    episodes_data = channel.get("episodes", {})
    episodes = []
    for ep in episodes_data.get("results", []):
        episodes.append(_format_channel_episode(ep, channel.get("title", "Unknown")))

    return {
        "podcastId": channel_id,
        "title": channel.get("title", "Unknown Channel"),
        "author": channel.get("title", "Unknown"),
        "description": channel.get("description", ""),
        "thumbnail": thumbnail,
        "episodes": episodes,
        "type": "channel",
    }


def get_home() -> list[dict]:
    """Obtener contenido de la página principal (recomendaciones)."""
    try:
        yt = _get_ytmusic()
        home = yt.get_home(limit=3)
        songs = []
        for section in home:
            if "contents" in section:
                for item in section["contents"]:
                    if item.get("videoId"):
                        songs.append(_format_song(item))
        return songs[:20]
    except Exception:
        return search_songs("top hits 2024", limit=20)


def get_song_info(video_id: str) -> dict | None:
    """Obtener información de una canción específica."""
    try:
        yt = _get_ytmusic()
        song = yt.get_song(video_id)
        return {
            "videoId": video_id,
            "title": song.get("videoDetails", {}).get("title", "Unknown"),
            "artist": song.get("videoDetails", {}).get("author", "Unknown"),
            "duration": song.get("videoDetails", {}).get("lengthSeconds", 0),
        }
    except Exception:
        return None


# ============ Funciones de biblioteca (requieren autenticación) ============


def get_library_playlists(limit: int = 500) -> list[dict]:
    """
    Obtener las playlists del usuario.
    Requiere autenticación.
    """
    yt = _get_ytmusic(require_auth=True)
    if yt is None:
        raise ValueError("Se requiere autenticación para acceder a la biblioteca")

    playlists = yt.get_library_playlists(limit=limit)
    return [_format_playlist(p) for p in playlists]


def get_liked_songs(limit: int = 5000) -> dict:
    """
    Obtener las canciones que le gustan al usuario.
    Requiere autenticación.
    """
    yt = _get_ytmusic(require_auth=True)
    if yt is None:
        raise ValueError("Se requiere autenticación para acceder a la biblioteca")

    liked = yt.get_liked_songs(limit=limit)
    tracks = liked.get("tracks", [])
    return {
        "title": "Canciones que me gustan",
        "trackCount": liked.get("trackCount", len(tracks)),
        "tracks": [_format_library_song(t) for t in tracks]
    }


def get_playlist(playlist_id: str, limit: int = 5000) -> dict:
    """
    Obtener detalles de una playlist específica.
    Requiere autenticación para playlists privadas.
    """
    yt = _get_ytmusic(require_auth=True)
    if yt is None:
        # Intentar con instancia pública (para playlists públicas)
        yt = _ytmusic_public

    playlist = yt.get_playlist(playlist_id, limit=limit)
    tracks = playlist.get("tracks", [])

    thumbnails = playlist.get("thumbnails", [])
    thumbnail = thumbnails[-1]["url"] if thumbnails else None

    return {
        "playlistId": playlist_id,
        "title": playlist.get("title", "Unknown Playlist"),
        "description": playlist.get("description", ""),
        "trackCount": playlist.get("trackCount", len(tracks)),
        "thumbnail": thumbnail,
        "tracks": [_format_library_song(t) for t in tracks if t.get("videoId")]
    }


def create_playlist(title: str, description: str = "", privacy: str = "PRIVATE") -> dict:
    """
    Crear una nueva playlist.
    Requiere autenticación.

    Args:
        title: Nombre de la playlist
        description: Descripción opcional
        privacy: PRIVATE, PUBLIC o UNLISTED

    Returns:
        dict con playlistId y status
    """
    yt = _get_ytmusic(require_auth=True)
    if yt is None:
        raise ValueError("Se requiere autenticación para crear playlists")

    playlist_id = yt.create_playlist(title, description, privacy_status=privacy)
    return {
        "playlistId": playlist_id,
        "title": title,
        "description": description,
        "privacy": privacy,
    }


def add_song_to_playlist(playlist_id: str, video_id: str) -> dict:
    """
    Añadir una canción a una playlist existente.
    Requiere autenticación.

    Args:
        playlist_id: ID de la playlist
        video_id: ID del video/canción a añadir

    Returns:
        dict con status
    """
    yt = _get_ytmusic(require_auth=True)
    if yt is None:
        raise ValueError("Se requiere autenticación para modificar playlists")

    result = yt.add_playlist_items(playlist_id, [video_id])

    if result.get("status") == "STATUS_SUCCEEDED" or result.get("playlistEditResults"):
        return {"success": True, "message": "Canción añadida correctamente"}
    else:
        return {"success": False, "message": "Error al añadir la canción"}


def remove_song_from_playlist(playlist_id: str, video_id: str, set_video_id: str = None) -> dict:
    """
    Eliminar una canción de una playlist.
    Requiere autenticación.

    Args:
        playlist_id: ID de la playlist
        video_id: ID del video/canción a eliminar
        set_video_id: setVideoId requerido por la API (opcional)

    Returns:
        dict con status
    """
    yt = _get_ytmusic(require_auth=True)
    if yt is None:
        raise ValueError("Se requiere autenticación para modificar playlists")

    # Si no tenemos setVideoId, necesitamos obtenerlo de la playlist
    if set_video_id is None:
        playlist = yt.get_playlist(playlist_id)
        for track in playlist.get("tracks", []):
            if track.get("videoId") == video_id:
                set_video_id = track.get("setVideoId")
                break

    if set_video_id is None:
        return {"success": False, "message": "Canción no encontrada en la playlist"}

    result = yt.remove_playlist_items(playlist_id, [{"videoId": video_id, "setVideoId": set_video_id}])

    if result == "STATUS_SUCCEEDED":
        return {"success": True, "message": "Canción eliminada correctamente"}
    else:
        return {"success": False, "message": "Error al eliminar la canción"}


def delete_playlist(playlist_id: str) -> dict:
    """
    Eliminar una playlist.
    Requiere autenticación.

    Args:
        playlist_id: ID de la playlist a eliminar

    Returns:
        dict con status
    """
    yt = _get_ytmusic(require_auth=True)
    if yt is None:
        raise ValueError("Se requiere autenticación para eliminar playlists")

    result = yt.delete_playlist(playlist_id)

    if result == "STATUS_SUCCEEDED" or result:
        return {"success": True, "message": "Playlist eliminada correctamente"}
    else:
        return {"success": False, "message": "Error al eliminar la playlist"}


# ============ Funciones de Podcasts y Canales ============


def get_library_podcasts_list(limit: int = 100) -> list[dict]:
    """
    Obtener los podcasts suscritos del usuario.
    Requiere autenticación.
    """
    yt = _get_ytmusic(require_auth=True)
    if yt is None:
        raise ValueError("Se requiere autenticación para acceder a los podcasts")

    podcasts = yt.get_library_podcasts(limit=limit)

    # Filter out items without valid channel.id (like "New Episodes", "Episodes for Later")
    def has_valid_id(p):
        channel = p.get("channel")
        if not channel or not isinstance(channel, dict):
            return False
        return channel.get("id") is not None

    return [_format_library_podcast(p) for p in podcasts if has_valid_id(p)]


def get_library_channels_list(limit: int = 100) -> list[dict]:
    """
    Obtener los canales suscritos del usuario.
    Requiere autenticación.
    """
    yt = _get_ytmusic(require_auth=True)
    if yt is None:
        raise ValueError("Se requiere autenticación para acceder a los canales")

    channels = yt.get_library_channels(limit=limit)
    return [_format_library_channel(c) for c in channels]


def get_channel_info(channel_id: str) -> dict:
    """
    Obtener información de un canal.
    """
    yt = _get_ytmusic(require_auth=True)
    if yt is None:
        yt = _ytmusic_public

    channel = yt.get_channel(channel_id)

    thumbnails = channel.get("thumbnails", [])
    thumbnail = thumbnails[-1]["url"] if thumbnails else None

    return {
        "channelId": channel_id,
        "title": channel.get("title", "Unknown Channel"),
        "description": channel.get("description", ""),
        "thumbnail": thumbnail,
        "episodeCount": channel.get("episodeCount", 0),
    }


def get_channel_episodes_paginated(channel_id: str, continuation: str = None) -> dict:
    """
    Obtener episodios de un canal con paginación.

    Args:
        channel_id: ID del canal
        continuation: Token de continuación para la siguiente página

    Returns:
        dict con episodes y continuation token
    """
    yt = _get_ytmusic(require_auth=True)
    if yt is None:
        yt = _ytmusic_public

    if continuation:
        # Usar get_channel_episodes con continuation
        result = yt.get_channel_episodes(channel_id, params=continuation)
    else:
        # Primera carga - obtener info del canal primero
        channel = yt.get_channel(channel_id)
        episodes_data = channel.get("episodes", {})

        # Formatear episodios
        episodes = []
        for ep in episodes_data.get("results", []):
            episodes.append(_format_channel_episode(ep, channel.get("title", "Unknown")))

        return {
            "episodes": episodes,
            "continuation": episodes_data.get("params"),
            "hasMore": episodes_data.get("params") is not None,
        }

    # Procesar resultado de continuation
    episodes = []
    for ep in result.get("results", []):
        episodes.append(_format_channel_episode(ep, ""))

    return {
        "episodes": episodes,
        "continuation": result.get("params"),
        "hasMore": result.get("params") is not None,
    }


def _format_library_podcast(podcast: dict) -> dict:
    """Formatear podcast de biblioteca."""
    channel = podcast.get("channel", {})
    thumbnails = podcast.get("thumbnails", [])
    thumbnail = thumbnails[-1]["url"] if thumbnails else None

    return {
        "podcastId": channel.get("id") if isinstance(channel, dict) else None,
        "title": podcast.get("title", "Unknown Podcast"),
        "author": channel.get("name", "Unknown") if isinstance(channel, dict) else "Unknown",
        "thumbnail": thumbnail,
        "type": "podcast",
    }


def _format_library_channel(channel: dict) -> dict:
    """Formatear canal de biblioteca."""
    thumbnails = channel.get("thumbnails", [])
    thumbnail = thumbnails[-1]["url"] if thumbnails else None

    # The channel name comes in 'artist' field from ytmusicapi
    title = (
        channel.get("artist")
        or channel.get("title")
        or channel.get("name")
        or "Unknown Channel"
    )

    return {
        "channelId": channel.get("browseId"),
        "title": title,
        "thumbnail": thumbnail,
        "type": "channel",
    }


def _format_channel_episode(episode: dict, channel_name: str) -> dict:
    """Formatear episodio de canal."""
    thumbnails = episode.get("thumbnails", [])
    thumbnail = thumbnails[-1]["url"] if thumbnails else None

    duration = episode.get("duration", None)
    duration_seconds = episode.get("duration_seconds", 0)

    return {
        "videoId": episode.get("videoId"),
        "title": episode.get("title", "Unknown Episode"),
        "artist": channel_name,
        "thumbnail": thumbnail,
        "duration": duration,
        "durationSeconds": duration_seconds,
        "date": episode.get("date"),
        "type": "episode",
    }


def _format_playlist(playlist: dict) -> dict:
    """Formatear datos de playlist para respuesta API."""
    thumbnails = playlist.get("thumbnails", [])
    thumbnail = thumbnails[-1]["url"] if thumbnails else None

    return {
        "playlistId": playlist.get("playlistId"),
        "title": playlist.get("title", "Unknown Playlist"),
        "thumbnail": thumbnail,
        "trackCount": playlist.get("count", 0),
    }


def _format_library_song(song: dict) -> dict:
    """Formatear datos de canción de biblioteca para respuesta API."""
    artists = song.get("artists", [])
    artist_name = artists[0]["name"] if artists else "Unknown Artist"

    thumbnails = song.get("thumbnails", [])
    thumbnail = thumbnails[-1]["url"] if thumbnails else None

    duration = song.get("duration", None)
    duration_seconds = song.get("duration_seconds", 0)

    return {
        "videoId": song.get("videoId"),
        "title": song.get("title", "Unknown Title"),
        "artist": artist_name,
        "thumbnail": thumbnail,
        "duration": duration,
        "durationSeconds": duration_seconds,
        "type": "song",
    }


def _format_song(song: dict) -> dict:
    """Formatear datos de canción para respuesta API."""
    artists = song.get("artists", [])
    artist_name = artists[0]["name"] if artists else "Unknown Artist"

    thumbnails = song.get("thumbnails", [])
    thumbnail = thumbnails[-1]["url"] if thumbnails else None

    duration = song.get("duration", None)
    duration_seconds = song.get("duration_seconds", 0)

    return {
        "videoId": song.get("videoId"),
        "title": song.get("title", "Unknown Title"),
        "artist": artist_name,
        "thumbnail": thumbnail,
        "duration": duration,
        "durationSeconds": duration_seconds,
        "type": "song",
    }


def _format_podcast(podcast: dict) -> dict:
    """Formatear datos de podcast para respuesta API."""
    author = podcast.get("author", {})
    author_name = author.get("name", "Unknown") if isinstance(author, dict) else str(author) if author else "Unknown"

    thumbnails = podcast.get("thumbnails", [])
    thumbnail = thumbnails[-1]["url"] if thumbnails else None

    return {
        "podcastId": podcast.get("browseId"),
        "title": podcast.get("title", "Unknown Podcast"),
        "author": author_name,
        "thumbnail": thumbnail,
        "type": "podcast",
    }


def _format_episode(episode: dict) -> dict:
    """Formatear datos de episodio de podcast para respuesta API."""
    podcast = episode.get("podcast", {})
    podcast_name = podcast.get("name", "Unknown Podcast") if isinstance(podcast, dict) else "Unknown Podcast"

    thumbnails = episode.get("thumbnails", [])
    thumbnail = thumbnails[-1]["url"] if thumbnails else None

    duration = episode.get("duration", None)
    duration_seconds = episode.get("duration_seconds", 0)

    return {
        "videoId": episode.get("videoId"),
        "title": episode.get("title", "Unknown Episode"),
        "artist": podcast_name,
        "thumbnail": thumbnail,
        "duration": duration,
        "durationSeconds": duration_seconds,
        "type": "episode",
    }


def _format_podcast_episode(episode: dict, podcast_name: str) -> dict:
    """Formatear datos de episodio desde la vista de podcast."""
    thumbnails = episode.get("thumbnails", [])
    thumbnail = thumbnails[-1]["url"] if thumbnails else None

    duration = episode.get("duration", None)
    duration_seconds = episode.get("duration_seconds", 0)

    # Fecha de publicación
    date = episode.get("date", None)

    return {
        "videoId": episode.get("videoId"),
        "title": episode.get("title", "Unknown Episode"),
        "artist": podcast_name,
        "thumbnail": thumbnail,
        "duration": duration,
        "durationSeconds": duration_seconds,
        "date": date,
        "description": episode.get("description", ""),
        "type": "episode",
    }
