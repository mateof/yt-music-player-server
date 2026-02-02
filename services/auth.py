"""Servicio de autenticación para YouTube Music."""

import hashlib
import json
import time
from pathlib import Path
from ytmusicapi import YTMusic

# Archivo donde se guardan las credenciales
# IMPORTANTE: El nombre debe contener "browser" para que ytmusicapi lo detecte correctamente
AUTH_FILE = Path(__file__).parent.parent / "userdata" / "browser.json"


def is_authenticated() -> bool:
    """Verificar si existe un archivo de autenticación válido."""
    return AUTH_FILE.exists()


def get_authenticated_ytmusic() -> YTMusic | None:
    """Obtener instancia de YTMusic autenticada, o None si no hay credenciales."""
    if not is_authenticated():
        return None
    try:
        # Leer el archivo y pasar el contenido como string JSON
        # Esto evita problemas de detección de tipo por nombre de archivo
        with open(AUTH_FILE, 'r') as f:
            auth_content = f.read()
        return YTMusic(auth_content)
    except Exception as e:
        print(f"[AUTH] Error creando YTMusic: {e}")
        return None


def _generate_sapisid_hash(sapisid: str, origin: str = "https://music.youtube.com") -> str:
    """
    Generar el hash SAPISIDHASH para el header Authorization.

    El formato es: SAPISIDHASH <timestamp>_<sha1(timestamp + " " + sapisid + " " + origin)>
    """
    timestamp = str(int(time.time()))
    hash_input = f"{timestamp} {sapisid} {origin}"
    sha1_hash = hashlib.sha1(hash_input.encode()).hexdigest()
    return f"SAPISIDHASH {timestamp}_{sha1_hash}"


def _extract_sapisid_from_cookies(cookie_str: str) -> str | None:
    """Extraer el valor de SAPISID o __Secure-3PAPISID de las cookies."""
    # Buscar SAPISID o las variantes seguras
    for cookie in cookie_str.split(';'):
        cookie = cookie.strip()
        if '=' in cookie:
            name, value = cookie.split('=', 1)
            name = name.strip()
            # SAPISID o las variantes __Secure-XPAPISID
            if name == 'SAPISID' or name in ['__Secure-1PAPISID', '__Secure-3PAPISID']:
                return value.strip()
    return None


def _build_headers_from_cookies(cookie_string: str) -> str:
    """
    Construir headers mínimos a partir de una string de cookies.

    Args:
        cookie_string: Cookies en formato "name=value; name2=value2" o JSON de EditThisCookie

    Returns:
        Headers en formato raw para ytmusicapi
    """
    # Si parece ser JSON (de EditThisCookie), parsearlo
    cookie_str = cookie_string.strip()

    if cookie_str.startswith('['):
        try:
            cookies_json = json.loads(cookie_str)
            # Formato EditThisCookie: [{"name": "...", "value": "..."}]
            cookie_parts = []
            for c in cookies_json:
                if isinstance(c, dict) and 'name' in c and 'value' in c:
                    cookie_parts.append(f"{c['name']}={c['value']}")
            cookie_str = "; ".join(cookie_parts)
        except json.JSONDecodeError:
            pass

    # Extraer SAPISID para generar el header Authorization
    sapisid = _extract_sapisid_from_cookies(cookie_str)
    authorization = ""
    if sapisid:
        authorization = _generate_sapisid_hash(sapisid)
        print(f"[AUTH] SAPISID encontrado, Authorization generado")
    else:
        print(f"[AUTH] ADVERTENCIA: No se encontró SAPISID en las cookies")

    # Construir headers con Authorization
    headers = f"""Cookie: {cookie_str}
Authorization: {authorization}
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
Accept: */*
Accept-Language: es-ES,es;q=0.9,en;q=0.8
X-Goog-AuthUser: 0
x-origin: https://music.youtube.com
Origin: https://music.youtube.com
Referer: https://music.youtube.com/"""

    return headers


def _detect_input_type(input_str: str) -> str:
    """
    Detectar el tipo de input: 'headers', 'cookies_json', o 'cookies_string'.
    """
    stripped = input_str.strip()

    # Si empieza con [, probablemente es JSON de EditThisCookie
    if stripped.startswith('['):
        return 'cookies_json'

    # Si tiene múltiples líneas con ":", probablemente son headers
    lines = stripped.split('\n')
    if len(lines) > 1:
        colon_lines = sum(1 for line in lines if ':' in line and not line.strip().startswith('Cookie'))
        if colon_lines >= 2:
            return 'headers'

    # Si contiene cookies típicas de YouTube, es una string de cookies
    if any(cookie in stripped for cookie in ['SAPISID', 'HSID', 'SSID', '__Secure-']):
        return 'cookies_string'

    # Por defecto, intentar como headers
    return 'headers'


def save_credentials(headers_raw: str) -> dict:
    """
    Guardar credenciales a partir de headers raw del navegador o cookies.

    Args:
        headers_raw: Headers copiados del navegador, cookies string, o JSON de EditThisCookie

    Returns:
        dict con status y mensaje
    """
    try:
        from ytmusicapi import setup

        input_type = _detect_input_type(headers_raw)
        print(f"[AUTH] Tipo detectado: {input_type}")

        # Si no son headers completos, construirlos desde cookies
        if input_type in ('cookies_json', 'cookies_string'):
            headers_raw = _build_headers_from_cookies(headers_raw)
            print(f"[AUTH] Headers construidos desde cookies")

        print(f"[AUTH] Headers a procesar (primeros 200 chars): {headers_raw[:200]}")

        # Usar setup() de ytmusicapi que sabe crear el formato correcto
        # Esto parsea los headers y crea el archivo en el formato esperado
        try:
            result = setup(filepath=str(AUTH_FILE), headers_raw=headers_raw)
            print(f"[AUTH] Setup completado, resultado: {result[:100] if result else 'None'}...")
        except Exception as setup_error:
            print(f"[AUTH] Error en setup: {setup_error}")
            # Si setup falla, intentar crear el archivo manualmente
            auth_data = _parse_headers_to_auth(headers_raw)
            print(f"[AUTH] Auth data keys: {list(auth_data.keys())}")
            with open(AUTH_FILE, 'w') as f:
                json.dump(auth_data, f, indent=2)
            print(f"[AUTH] Archivo guardado manualmente")

        print(f"[AUTH] Archivo guardado en {AUTH_FILE}")

        # Leer el contenido del archivo
        with open(AUTH_FILE, 'r') as f:
            content = f.read()
        print(f"[AUTH] Contenido del archivo: {content[:300]}...")

        # Verificar que funciona creando una instancia
        # Pasar el contenido JSON directamente en lugar del path
        ytmusic = YTMusic(content)
        print(f"[AUTH] YTMusic instanciado")

        # Intentar obtener las playlists para verificar que la autenticación funciona
        try:
            playlists = ytmusic.get_library_playlists(limit=1)
            print(f"[AUTH] Playlists obtenidas: {len(playlists)}")
        except Exception as e:
            print(f"[AUTH] Error obteniendo playlists: {e}")
            raise Exception(f"Autenticación fallida. Las cookies pueden estar incompletas o expiradas.")

        return {
            "success": True,
            "message": "Autenticación guardada correctamente"
        }
    except Exception as e:
        print(f"[AUTH] Error: {e}")
        import traceback
        traceback.print_exc()

        # Si falla, eliminar el archivo si se creó
        if AUTH_FILE.exists():
            AUTH_FILE.unlink()

        error_msg = str(e)
        if "KeyError" in error_msg or "cookie" in error_msg.lower():
            error_msg = "Cookies incompletas. Asegúrate de copiar TODAS las cookies de music.youtube.com"

        return {
            "success": False,
            "message": f"Error: {error_msg}"
        }


def _parse_headers_to_auth(headers_raw: str) -> dict:
    """
    Parsear headers raw a formato de autenticación de ytmusicapi.
    El formato esperado por ytmusicapi para browser auth usa headers en minúsculas.
    """
    headers = {}
    cookie = ""

    for line in headers_raw.strip().split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()

            if key.lower() == 'cookie':
                cookie = value
            else:
                # Guardar con key en minúsculas
                headers[key.lower()] = value

    # Si no hay authorization, intentar generarlo desde SAPISID
    authorization = headers.get("authorization", "")
    if not authorization and cookie:
        sapisid = _extract_sapisid_from_cookies(cookie)
        if sapisid:
            authorization = _generate_sapisid_hash(sapisid)
            print(f"[AUTH] Authorization generado desde SAPISID")

    # Formato esperado por ytmusicapi para BROWSER auth
    # IMPORTANTE: Necesita tanto "authorization" como "cookie"
    auth_data = {
        "accept": "*/*",
        "accept-language": headers.get("accept-language", "en-US,en;q=0.9"),
        "authorization": authorization,
        "content-type": "application/json",
        "cookie": cookie,
        "user-agent": headers.get("user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
        "x-goog-authuser": headers.get("x-goog-authuser", "0"),
        "x-origin": "https://music.youtube.com",
    }

    return auth_data


def logout() -> dict:
    """Eliminar las credenciales guardadas."""
    try:
        if AUTH_FILE.exists():
            AUTH_FILE.unlink()
        return {
            "success": True,
            "message": "Sesión cerrada correctamente"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error al cerrar sesión: {str(e)}"
        }


def get_auth_status() -> dict:
    """Obtener el estado de autenticación actual."""
    if not is_authenticated():
        return {
            "authenticated": False,
            "message": "No autenticado"
        }

    # Verificar que las credenciales son válidas
    ytmusic = get_authenticated_ytmusic()
    if ytmusic is None:
        return {
            "authenticated": False,
            "message": "Credenciales inválidas o expiradas"
        }

    return {
        "authenticated": True,
        "message": "Autenticado"
    }
