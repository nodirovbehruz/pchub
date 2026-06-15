FROM python:3.11-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        git \
        curl \
        make \
        gdal-bin \
        libgdal-dev \
        python3-gdal \
        binutils \
        libproj-dev \
        netcat-traditional \
        gettext \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8000

# Run the application in development mode
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
