# Rosetta Stone Bot

Bot de automatización para Rosetta Stone usando Playwright, implementado con una arquitectura modular siguiendo principios de diseño limpio.

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
│   └── frame_finder.py    # Búsqueda en frames/iframes
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

## 🚀 Uso

### Ejecución Local

```bash
# Instalar dependencias
uv sync

# Ejecutar workflow de historias
python main.py --workflow stories

# Ejecutar workflow de lecciones
python main.py --workflow lesson
```

### Docker

```powershell
# Build
docker build -t script-rosseta:latest .

# Run (headless)
docker run --rm script-rosseta:latest

# Run con UI
docker run --rm -e PLAYWRIGHT_HEADLESS=0 script-rosseta:latest
```

## 📦 Estructura de Módulos

### Core

Constantes y utilidades fundamentales compartidas por todo el proyecto.

### Services

Servicios de negocio que encapsulan lógica reutilizable:

- `AudioPlayerService`: Play, pause, rewind
- `ModeSwitcherService`: Cambio listen/read
- `DebugService`: Screenshots y dumps
- `FrameFinderService`: Búsqueda en iframes

### Workflows

Flujos de automatización completos:

- `StoriesWorkflow`: Procesa todas las historias en loop
- `LessonWorkflow`: Repite una lección infinitamente

### Pages

Page Objects que representan páginas de la aplicación.

### Components

Componentes UI reutilizables (modales, banners).

### Locators

Selectores CSS/XPath centralizados por página.
