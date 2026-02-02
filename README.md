# YouTube Music API

Backend API to interact with YouTube Music. Search songs, stream audio, manage playlists, and download content.

## Features

- Search songs, podcasts, and episodes
- Stream audio from YouTube Music
- Download songs as MP3 (320kbps)
- Access user library (playlists, liked songs)
- Create and manage playlists
- Subscribe to podcasts and channels
- Local file management for downloaded content
- Audio caching system

## Requirements

- Python 3.10+
- FFmpeg installed on the system
- Dependencies: FastAPI, ytmusicapi, yt-dlp, uvicorn

## Quick Start

### Using Docker (Recommended)

```bash
docker pull ghcr.io/mateof/yt-music-player-server:latest
docker run -d -p 8000:8000 -v ./userdata:/app/userdata -v ./data:/app/data ghcr.io/mateof/yt-music-player-server:latest
```

Or with docker-compose:

```bash
docker compose up -d
```

### Manual Installation

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

The server will be available at `http://localhost:8000`

## Configuration

### Authentication

To access your YouTube Music library, you need to provide your browser credentials:

1. Open YouTube Music in your browser
2. Open DevTools (F12) > Network tab
3. Find a request to `music.youtube.com`
4. Copy the `Cookie` and `Authorization` headers
5. Save them in `userdata/browser.json`

See `userdata/browser.json.example` for the expected format.

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Main Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/search?q={query}` | Search songs |
| `GET /api/stream/{video_id}` | Stream audio |
| `GET /api/download/{video_id}` | Download as MP3 |
| `GET /api/library/playlists` | Get user playlists |
| `GET /api/library/liked-songs` | Get liked songs |
| `GET /api/podcasts/library` | Get subscribed podcasts |

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Related Projects

- [yt-music-player](https://github.com/mateof/yt-music-player) - Frontend web application
