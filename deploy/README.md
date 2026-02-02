# Deployment

Deploy YouTube Music API using Docker.

## Quick Start

1. Copy this folder to your server
2. Create `userdata/browser.json` with your YouTube Music credentials:
   ```bash
   mkdir -p userdata
   cp ../userdata/browser.json.example userdata/browser.json
   # Edit userdata/browser.json with your credentials
   ```
3. Start the service:
   ```bash
   docker compose up -d
   ```

## Configuration

### userdata/browser.json

Required for accessing your YouTube Music library (playlists, liked songs, etc.).

To get your credentials:
1. Open YouTube Music in your browser
2. Open DevTools (F12) > Network tab
3. Find a request to `music.youtube.com`
4. Copy the `Cookie` and `Authorization` headers
5. Paste them in `userdata/browser.json`

### Volumes

- `./data` - Downloaded music files
- `./userdata` - Authentication credentials and user config

## Commands

```bash
# Start
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down

# Update to latest version
docker compose pull && docker compose up -d

# Use specific version
# Edit docker-compose.yml and change :latest to :1.0.0
```

## Ports

- `8000` - API server (http://localhost:8000)
- API docs available at http://localhost:8000/docs
