FROM python:3.12

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /uvx /bin/

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
  apt-get update && \
  apt-get --no-install-recommends install -y libgdal-dev libgeos-dev

RUN mkdir /static

WORKDIR /code
COPY . /code

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Ensure uv uses python from the image
ENV UV_NO_MANAGED_PYTHON=true

# Docker cache dir is on different volume than the project -> needs copy mode
ENV UV_LINK_MODE=copy

# Create venv outside the project directory instead of .venv subdirectory
ENV UV_PROJECT_ENVIRONMENT=/root/venv

# Add venv to path so python commands use it by default
ENV PATH="/root/venv/bin:$PATH"
ENV VIRTUAL_ENV="/root/venv"

EXPOSE 8002

# Install virtual env. Compile dependencies for faster startup.
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --compile-bytecode

CMD ["uv", "run", "manage.py", "runserver", "0.0.0.0:8002"]
