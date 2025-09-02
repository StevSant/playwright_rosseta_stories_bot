FROM python:3.13-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=off \
  PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Copy project files
COPY pyproject.toml pyproject.toml
COPY uv.lock uv.lock
COPY . /app

# Install system dependencies required by Playwright browsers
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
  apt-transport-https \
  ca-certificates \
  curl \
  fonts-liberation \
  gnupg \
  libasound2 \
  libatk-bridge2.0-0 \
  libatk1.0-0 \
  libcups2 \
  libgbm1 \
  libnss3 \
  libx11-xcb1 \
  libxcomposite1 \
  libxrandr2 \
  libxkbcommon0 \
  && rm -rf /var/lib/apt/lists/*

# Install pip-tools and install dependencies from pyproject/lock
RUN python -m pip install --upgrade pip setuptools pip-tools && \
  python -m pip install "playwright>=1.55.0"

# Install playwright browsers (all supported browsers)
RUN python -m playwright install --with-deps

# Expose nothing (this is a script), set non-root user if desired
# Use root by default so Playwright can run without extra permissions in CI/local

ENTRYPOINT ["python", "./main.py"]
