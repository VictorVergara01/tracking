# Despliegue en Proxmox (nginx + Cloudflare Tunnel)

Guía para correr el servidor de TrackFlow en tu Proxmox, detrás del nginx que ya
maneja tus dominios y que está conectado a Cloudflare por tunnel.

## Arquitectura del despliegue

```
Internet
   │  HTTPS
   ▼
Cloudflare  ──(tunnel)──▶  nginx (Proxmox)  ──proxy──▶  uvicorn :8000
                          maneja dominios               TrackFlow (FastAPI)
                                                          ├─ API  (/auth, /processes, ...)
                                                          └─ Web  (/ui  ·  / redirige a /ui)
```

- Cloudflare termina el **TLS** y envía el tráfico por el tunnel a tu nginx.
- nginx hace **reverse proxy** del dominio hacia `127.0.0.1:8000`.
- FastAPI sirve **la API y la web en el mismo origen**, así que con un solo
  dominio (`https://trackflow.tudominio.com`) entran Windows, Mac, Linux y
  celulares — sin instalar nada.

---

## 1. Preparar el servicio en el LXC/VM

```bash
# como root en el contenedor/VM
apt update && apt install -y python3 python3-venv git nginx
adduser --system --group trackflow

git clone https://github.com/VictorVergara01/tracking.git /opt/tracking
cd /opt/tracking/server
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
chown -R trackflow:trackflow /opt/tracking
```

## 2. Servicio systemd

```bash
cp /opt/tracking/deploy/trackflow.service /etc/systemd/system/trackflow.service
# EDITÁ el archivo y poné una clave secreta real:
nano /etc/systemd/system/trackflow.service     # TRACKFLOW_SECRET=...

systemctl daemon-reload
systemctl enable --now trackflow
systemctl status trackflow          # debe quedar "active (running)"
curl -s http://127.0.0.1:8000/health   # {"status":"ok"}
```

> **Importante:** generá una clave fuerte y única para `TRACKFLOW_SECRET`
> (firma los tokens). Ejemplo: `openssl rand -hex 32`.

## 3. nginx

```bash
cp /opt/tracking/deploy/nginx-trackflow.conf /etc/nginx/sites-available/trackflow
# EDITÁ server_name con tu dominio:
nano /etc/nginx/sites-available/trackflow
ln -s /etc/nginx/sites-available/trackflow /etc/nginx/sites-enabled/trackflow
nginx -t && systemctl reload nginx
```

## 4. Cloudflare Tunnel

Ya tenés el tunnel funcionando. Solo agregá (o reutilizá) un **hostname público**
que apunte a tu nginx:

- **Hostname:** `trackflow.tudominio.com`
- **Service:** `http://localhost:80` (o la IP:puerto donde nginx escucha)

Si usás archivo de config del tunnel (`cloudflared`), algo así:

```yaml
ingress:
  - hostname: trackflow.tudominio.com
    service: http://localhost:80
  - service: http_status:404
```

Luego `cloudflared tunnel route dns <tunnel> trackflow.tudominio.com` (si no está
ya en el dashboard) y reiniciá el servicio del tunnel.

## 5. Probar

- Abrí `https://trackflow.tudominio.com` → redirige a `/ui/` (login web).
- Entrá con `manager / manager123` (cambiá las credenciales demo después).
- API y docs: `https://trackflow.tudominio.com/docs`.

## 6. Datos de ejemplo (opcional, para demos)

Pobla el dashboard con procesos de muestra (tiempos por etapa ya medidos, un
proceso atrasado, uno completo con lead time, cuello de botella):

```bash
cd /opt/tracking/server
.venv/bin/python seed_demo.py           # crea/repone los procesos "[Demo]"
.venv/bin/python seed_demo.py --clear    # los borra
```
No tocan tus procesos reales (se reconocen por el prefijo `[Demo]`). Es
idempotente: podés correrlo las veces que quieras.

---

## ✅ Checklist antes de producción / v1

- [ ] `TRACKFLOW_SECRET` propio y fuerte (`openssl rand -hex 32`), no la clave de dev.
- [ ] Cambiar o borrar las credenciales demo (`manager`, `cliente1`, `cliente2`).
- [ ] `systemctl status trackflow` en `active (running)` y `enable`d (arranca solo).
- [ ] nginx + tunnel: el dominio responde por HTTPS y redirige `/` → `/ui/`.
- [ ] Probar end-to-end en el dominio: login web, crear proceso, avanzar etapa.
- [ ] Plan de backup de `server/app.db` (copiá también `app.db-wal` si existe).
- [ ] (opcional) `seed_demo.py` si querés datos de muestra para la presentación.

---

## Actualizaciones

```bash
cd /opt/tracking && git pull
cd server && .venv/bin/pip install -r requirements.txt
systemctl restart trackflow
```
El esquema de la base se migra solo al arrancar (`ensure_schema`), sin perder datos.

## Notas

- **Base de datos:** SQLite en `server/app.db` (modo WAL). Hacé backup de ese
  archivo. Si crecés a muchos usuarios concurrentes escribiendo, migrar a
  PostgreSQL es directo (cambiar la URL del engine en `server/models.py`).
- **Credenciales demo:** borralas o cambiá las contraseñas antes de uso real
  (usuarios `manager`, `cliente1`, `cliente2` en `server/models.py`).
- **Clientes de escritorio:** opcionales. La web cubre todos los sistemas; los
  `.exe`/`.app` se generan con GitHub Actions (ver `README.md`) si los querés.
