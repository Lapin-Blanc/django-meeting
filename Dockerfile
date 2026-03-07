FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project source
COPY . .

# Collect static files at build time
ENV DJANGO_SECRET_KEY=build-time-placeholder-not-used-in-production
RUN python manage.py collectstatic --noinput

# Create directories for runtime data
RUN mkdir -p /data /app/media

# Expose default gunicorn port (overridable via DJANGO_PORT)
EXPOSE 8768

# Entrypoint: migrate, optional superuser creation, then gunicorn
CMD ["sh", "-c", "python manage.py migrate --noinput && if [ \"${DJANGO_CREATE_SUPERUSER:-0}\" = \"1\" ]; then python manage.py createsuperuser --noinput || true; fi && gunicorn config.wsgi:application --bind 0.0.0.0:${DJANGO_PORT:-8768} --workers 2 --timeout 60"]
