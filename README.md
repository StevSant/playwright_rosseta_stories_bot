# script-rosseta — Docker

Este repositorio contiene un bot de Playwright (`script.py`). Este Dockerfile construye una imagen Python 3.13 con Playwright y los navegadores necesarios instalados.

Build:

```powershell
docker build -t script-rosseta:latest .
```

Run (modo headless por defecto):

```powershell
docker run --rm script-rosseta:latest
```

Ejecutar sin headless (abrirá navegador con UI, no recomendado en servidores):

```powershell
docker run --rm -e PLAYWRIGHT_HEADLESS=0 script-rosseta:latest
```

Notas:

- La imagen instala Playwright y sus navegadores con `playwright install --with-deps`.
- Si requiere ejecutar como usuario no-root o añadir credenciales de forma segura, monte un archivo o use secretos en su orquestador.
