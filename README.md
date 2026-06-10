# Rosetta Stone Bot

Bot de automatización para Rosetta Stone usando Playwright, implementado con una arquitectura modular siguiendo principios de diseño limpio.

## ⚡ Estrategia: rápido primero, bot completo como fallback

El punto de entrada por defecto es **`run.py`**, un orquestador con dos fases:

1. **`fast_stories_v3.py`** — abre N sesiones paralelas que acreditan horas de
   Stories directamente vía la API `app_usage` (rápido; es lo que mueve el panel
   de admin de la institución).
2. **Fallback** — si v3 no progresa (ninguna sesión establecida, o la API deja
   de acreditar horas porque cambió/fue bloqueada), el orquestador lanza el bot
   completo de Playwright en `rosetta_bot`, que reproduce las Stories de forma
   real en un navegador.

```bash
uv run run.py              # usa .env
uv run run.py .env_daniela # archivo .env específico (misma convención que v3)
```

`main.py` se mantiene como entrada directa del bot completo (solo navegador),
sin la fase rápida.

## ⏱️ Sistema de Tracking de Horas

El bot incluye un sistema automático de seguimiento de horas por usuario:

- ✅ **Tracking automático**: Registra el tiempo de cada sesión
- ✅ **Persistencia**: Los datos se guardan en `data/time_tracking.json`
- ✅ **Meta de 35 horas**: Notifica cuando se completa el objetivo
- ✅ **Reportes**: Genera reportes automáticos al completar
- ✅ **Multi-usuario**: Soporta múltiples usuarios identificados por email

### Estructura de datos

```
data/
├── time_tracking.json     # Datos de todos los usuarios
└── reports/
    └── reporte_usuario_20260109_123456.txt
```

## 🚀 Uso

### Variables de Entorno

Crear un archivo `.env`:

```env
ROSETTA_EMAIL=tu_email@ejemplo.com
ROSETTA_PASSWORD=tu_password
BROWSER_HEADLESS=1
LESSON_NAME=A Visit to Hollywood|Una visita a Hollywood
TARGET_HOURS=35
DEBUG=1
```

| Variable | Descripción | Default |
|----------|-------------|---------|
| `ROSETTA_EMAIL` | Email de la cuenta Rosetta Stone | (requerido) |
| `ROSETTA_PASSWORD` | Contraseña | (requerido) |
| `BROWSER_HEADLESS` | Modo headless (1=sí, 0=no) | `1` |
| `LESSON_NAME` | Nombre de la lección (regex) | `A Visit to Hollywood\|Una visita a Hollywood` |
| `TARGET_HOURS` | Horas objetivo por usuario | `35` |
| `DEBUG` | Habilitar debug/screenshots | `1` |
| `FALLBACK_MIN_HOURS` | Si v3 acredita menos horas que esto, se activa el bot completo | `0.1` |
| `FALLBACK_MODE` | Workflow del bot en el fallback: `stories` o `lesson` | `stories` |
| `PARALLEL_SESSIONS` | Sesiones paralelas de `fast_stories_v3` | `5` |

### Ejecución Local

```bash
# Instalar dependencias
uv sync

# Ejecutar el orquestador (rápido + fallback) — recomendado
uv run run.py

# Ejecutar solo el bot completo de navegador
uv run main.py

# Ver estado de horas de todos los usuarios
uv run status.py
```

## 🐳 Docker

### Build

```bash
docker build -t rosseta-playwright-image .
```

### Ejecutar el bot

```bash
# Un solo container
docker run --rm \
  -v tracking-data:/app/data \
  --env-file .env \
  rosseta-playwright-image

# Con docker-compose (múltiples usuarios)
docker-compose up -d
```

### Ver estado de horas

```bash
# Desde un container en ejecución (recomendado)
docker compose exec jandry uv run status.py

# O con docker run (usar nombre completo del volumen)
docker run --rm \
  -v playwright_rosseta_stories_bot_tracking-data:/app/data \
  rosseta-playwright-image \
  uv run status.py
```

### Ver datos de tracking

```bash
# Desde un container en ejecución (recomendado)
docker compose exec jandry cat /app/data/time_tracking.json

# Ver archivos de datos
docker compose exec jandry ls -la /app/data/

# Ver reportes generados
docker compose exec jandry ls -la /app/data/reports/

# Alternativa con docker run (usar nombre completo del volumen)
docker run --rm \
  -v playwright_rosseta_stories_bot_tracking-data:/app/data \
  rosseta-playwright-image \
  cat /app/data/time_tracking.json
```

### Copiar datos al host

```bash
# Copiar carpeta data al directorio actual
docker run --rm \
  -v playwright_rosseta_stories_bot_tracking-data:/app/data \
  -v $(pwd):/backup \
  rosseta-playwright-image \
  cp -r /app/data /backup/data-backup
```

### Ver volúmenes disponibles

```bash
# Listar todos los volúmenes de Docker
docker volume ls

# El volumen de docker-compose tendrá el prefijo del proyecto:
# playwright_rosseta_stories_bot_tracking-data
```

### Docker Compose

El archivo `docker-compose.yml` permite ejecutar múltiples bots para diferentes usuarios:

```yaml
version: '3'

volumes:
  tracking-data:  # Volumen compartido para persistir datos

services:
  usuario1:
    image: rosseta-playwright-image
    env_file:
      - .env_usuario1
    volumes:
      - tracking-data:/app/data
    restart: always

  usuario2:
    image: rosseta-playwright-image
    env_file:
      - .env_usuario2
    volumes:
      - tracking-data:/app/data
    restart: always
```

```bash
# Iniciar todos los bots
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener todos
docker-compose down
```

## 🏗️ Arquitectura

El proyecto sigue una arquitectura de capas con separación de responsabilidades:

```
rosetta_bot/
├── core/           # Constantes y utilidades fundamentales
│   ├── timeouts.py     # Timeouts en milisegundos
│   ├── wait_times.py   # Tiempos de espera en segundos
│   ├── urls.py         # URLs de la aplicación
│   └── logger.py       # Sistema centralizado de logging
│
├── services/       # Servicios de negocio reutilizables
│   ├── audio_player.py    # Control de reproducción de audio
│   ├── mode_switcher.py   # Cambio entre modos escuchar/leer
│   ├── debug_service.py   # Capturas y dumps de depuración
│   ├── frame_finder.py    # Búsqueda en frames/iframes
│   └── time_tracker.py    # ⏱️ Tracking de horas por usuario
│
├── workflows/      # Flujos de automatización
│   ├── base_workflow.py     # Clase base abstracta
│   ├── stories_workflow.py  # Procesamiento de historias
│   └── lesson_workflow.py   # Ciclo de lecciones
│
├── pages/          # Page Objects (Patrón POM)
│   ├── base_page.py      # Funcionalidad común
│   ├── login_page.py     # Autenticación
│   ├── launchpad_page.py # Navegación inicial
│   ├── stories_page.py   # Página de historias
│   └── lesson_page.py    # Página de lecciones
│
├── components/     # Componentes UI reutilizables
│   ├── audio_modal.py    # Modal de audio
│   ├── voice_modal.py    # Modal de voz
│   └── cookie_consent.py # Banner de cookies
│
├── locators/       # Selectores centralizados
│   ├── login_locators.py
│   ├── stories_locators.py
│   ├── lesson_locators.py
│   ├── launchpad_locators.py
│   └── common_locators.py
│
├── bot.py          # Orquestador principal
├── browser.py      # Gestión del navegador
├── config.py       # Configuración
└── exceptions.py   # Excepciones personalizadas
```

## 🎯 Principios de Diseño

- **SRP (Single Responsibility)**: Cada archivo tiene una única responsabilidad
- **POM (Page Object Model)**: Páginas encapsuladas como objetos
- **Service Layer**: Lógica reutilizable separada en servicios
- **Workflow Pattern**: Flujos de automatización como clases independientes

## 📦 Módulos

### Services

| Servicio | Descripción |
|----------|-------------|
| `AudioPlayerService` | Play, pause, rewind |
| `ModeSwitcherService` | Cambio listen/read |
| `DebugService` | Screenshots y dumps |
| `FrameFinderService` | Búsqueda en iframes |
| `TimeTracker` | ⏱️ Tracking de horas |

### Workflows

| Workflow | Descripción |
|----------|-------------|
| `StoriesWorkflow` | Procesa todas las historias en loop |
| `LessonWorkflow` | Repite una lección infinitamente |

## 📊 Ejemplo de Reporte

Cuando un usuario completa las 35 horas, se genera automáticamente:

```
============================================================
REPORTE DE HORAS - ROSETTA STONE BOT
============================================================

Usuario: usuario@ejemplo.com
Fecha del reporte: 2026-01-09 15:30:45

----------------------------------------
RESUMEN
----------------------------------------
Horas objetivo: 35.0h
Horas completadas: 35.25h (35:15:00)
Progreso: 100.0%
Horas restantes: 0.00h
Estado: ✅ COMPLETADO

Total de sesiones: 12
Primera sesión: 2026-01-05
Última actualización: 2026-01-09
Fecha de completado: 2026-01-09

----------------------------------------
HISTORIAL DE SESIONES
----------------------------------------
    1. 2026-01-05 10:00:00 | 03:00:00 | InfiniteLesson
    2. 2026-01-05 14:00:00 | 02:30:00 | InfiniteLesson
    ...

============================================================
Generado automáticamente por Rosetta Stone Bot
============================================================
```
