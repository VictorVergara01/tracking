# TrackFlow

Sistema de monitoreo de procesos con métricas de ingeniería industrial
(tiempo por etapa, lead time, cuellos de botella, alertas de atraso) y
tutorial guiado por rol.

Arquitectura **cliente–servidor**: la API y la base de datos viven en tu
servidor. Hay **dos clientes** que consumen la misma API:

- **Web** (recomendado) — servida por el propio FastAPI en `/ui`. Una sola URL,
  entra desde **Windows, macOS, Linux y celular** sin instalar nada. Ideal para
  equipos mixtos y gente en campo.
- **Escritorio** (PyQt6) — `.exe` (Windows) / `.app` (macOS), opcional.

Así pueden usarlo a la vez quienes están en la oficina (red local) y quienes
trabajan en campo (remoto).

> 🚀 **Despliegue en producción** (Proxmox + nginx + Cloudflare Tunnel):
> ver **[DEPLOY.md](DEPLOY.md)**.

```
┌─────────────┐        HTTP/JSON        ┌────────────────────────┐
│  Cliente    │  ───────────────────▶   │  Servidor (tu máquina) │
│  .exe/.app  │   Bearer token (JWT)    │  FastAPI + SQLite       │
└─────────────┘                         └────────────────────────┘
   oficina y campo                          API en :8000  ·  /docs
```

```
tracking/                  ← cliente PyQt (este es el repo)
  main.py, api_client.py, auth.py, views/...
  trackflow.spec           ← build del cliente (PyInstaller)
  server/                  ← API FastAPI
    main.py, models.py, schemas.py, auth.py, requirements.txt
  .github/workflows/build.yml   ← compila .exe + .app en la nube
```

---

## 1. Servidor (API + base de datos)

### Instalación
```bash
cd server
python -m venv .venv
# Windows:  .\.venv\Scripts\Activate.ps1
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
```

### Ejecución
```bash
# Solo accesible desde la misma máquina (pruebas):
uvicorn main:app --reload

# Accesible desde la red (oficina + campo): escucha en todas las interfaces
uvicorn main:app --host 0.0.0.0 --port 8000
```
- Documentación interactiva: `http://<servidor>:8000/docs`
- La base `server/app.db` (SQLite, modo WAL) se crea sola con usuarios demo.

### Variables de entorno (producción)
| Variable | Para qué | Default |
|---|---|---|
| `TRACKFLOW_SECRET` | Clave para firmar los tokens JWT. **Cambiala** (≥32 caracteres). | clave de desarrollo |
| `TRACKFLOW_TOKEN_TTL_HOURS` | Vigencia del token. | 720 (30 días) |

```bash
# ejemplo
export TRACKFLOW_SECRET="una-clave-larga-y-secreta-de-al-menos-32-bytes"
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Credenciales demo
| Rol | Usuario | Contraseña |
|---|---|---|
| Gerente | `manager` | `manager123` |
| Cliente | `cliente1` | `cliente123` |
| Cliente | `cliente2` | `cliente123` |

---

## 2. Conectividad: oficina y campo

El cliente tiene un campo **"Servidor"** en el login (se recuerda entre usos).

- **Oficina (LAN):** apuntá a la IP local del servidor, ej. `http://192.168.1.50:8000`.
- **Campo (remoto):** el servidor debe ser alcanzable desde internet. Opciones:
  - **IP pública / dominio + port-forwarding** del puerto 8000 en el router.
  - **Túnel** (sin tocar el router), ideal para la demo:
    ```bash
    # Cloudflare Tunnel
    cloudflared tunnel --url http://localhost:8000
    # o ngrok
    ngrok http 8000
    ```
    Te da una URL pública `https://...` que pegás en el campo "Servidor".

> ⚠️ **Para acceso remoto usá HTTPS.** Viajan credenciales y tokens. Lo más
> simple es poner un reverse proxy con TLS delante (ej. **Caddy**):
> ```
> trackflow.tudominio.com {
>     reverse_proxy localhost:8000
> }
> ```
> Caddy gestiona el certificado automáticamente. Los túneles de Cloudflare/ngrok
> ya entregan HTTPS.

> SQLite (WAL) rinde bien para una demo y equipos chicos/medianos. Si crecés a
> muchos usuarios concurrentes escribiendo, migrar a PostgreSQL es directo
> (cambiar la URL del engine en `server/models.py`).

---

## 3. Cliente web (recomendado, multiplataforma)

No requiere instalación. Una vez que el servidor está corriendo, abrí en el
navegador:

```
http://<servidor>:8000/        →  redirige a /ui (login)
```

Funciona en Windows, macOS, Linux y móvil. Tiene **paridad completa** con el
escritorio: login/registro, dashboard del gerente (crear/editar/eliminar,
avanzar etapas, indicadores y cuello de botella), vista del cliente con línea de
tiempo, fechas límite/atrasos y tutorial guiado por rol. Como se sirve desde el
mismo origen que la API, no hace falta configurar URL de servidor.

## 4. Cliente de escritorio (opcional)

### Para usuarios finales (binario)
1. Descargá **`TrackFlow.exe`** (Windows) o **`TrackFlow-macos.zip`** (macOS) desde
   la sección Releases / Artifacts del repo.
2. **Windows:** doble clic en `TrackFlow.exe`.
   **macOS:** descomprimí el zip y abrí `TrackFlow.app`.
   - La primera vez macOS puede bloquearlo por ser de un desarrollador no
     identificado: clic derecho → **Abrir**, o:
     `xattr -dr com.apple.quarantine TrackFlow.app`
3. En **"Servidor"** poné la URL de tu API e iniciá sesión.

### Desde el código fuente
```bash
python -m venv .venv
# Windows:  .\.venv\Scripts\Activate.ps1
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

---

## 5. Generar los instaladores de escritorio

### Opción A — GitHub Actions (recomendada, no necesitás Mac)
El workflow `.github/workflows/build.yml` compila **Windows y macOS** en la nube.
1. Subí el repo a GitHub.
2. Disparalo desde **Actions → Build desktop client → Run workflow**, o
   creando un tag de versión:
   ```bash
   git tag v1.0.0 && git push origin v1.0.0
   ```
   Con el tag, además **publica los binarios en un Release**.
3. Descargá `TrackFlow-windows` y `TrackFlow-macos` desde los artifacts/Release.

### Opción B — Local (solo tu plataforma actual)
```bash
pip install pyinstaller
pyinstaller --noconfirm trackflow.spec
# resultado en dist/  (TrackFlow.exe en Windows, TrackFlow.app en macOS)
```
> PyInstaller **no** hace cross-compile: el `.app` de macOS solo se genera en una
> Mac. Por eso para Mac conviene la Opción A.
