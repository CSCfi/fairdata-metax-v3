FROM python:3.12

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN pip install --upgrade pip wheel
RUN mkdir /static
COPY dev-requirements.txt /code/
WORKDIR /code

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
  apt-get update && \
  apt-get --no-install-recommends install -y libgdal-dev libgeos-dev

RUN --mount=type=cache,target=/root/.cache/pip \
  pip install -r dev-requirements.txt

COPY . /code

EXPOSE 8002

CMD ["python", "manage.py", "runserver", "0.0.0.0:8002"]
