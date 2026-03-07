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

# Collect static files at build time (requires SECRET_KEY env var)
ENV SECRET_KEY=build-time-placeholder-not-used-in-production
RUN python manage.py collectstatic --noinput

# Create directories for runtime data
RUN mkdir -p /data /app/media

# Expose gunicorn port
EXPOSE 8768

# Entrypoint: migrate then start gunicorn
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8768 --workers 2 --timeout 60"]
