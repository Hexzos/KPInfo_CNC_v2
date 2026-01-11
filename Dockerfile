FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copiamos todo el proyecto
COPY . /app

# Fly inyecta PORT; Config.py lo lee.
# Expose es informativo, no obligatorio.
EXPOSE 8080

# Arranque del servidor
CMD ["python", "-m", "server.server"]
