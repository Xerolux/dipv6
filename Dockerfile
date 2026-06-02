FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY dynipv6_service.py .

# Create necessary directories
RUN mkdir -p /etc/dynipv6 /var/lib/dynipv6 /var/log/dynipv6

# Create www-data user
RUN useradd -m -u 33 www-data || true

# Set permissions
RUN chown -R www-data:www-data /var/lib/dynipv6 /var/log/dynipv6 /app

# Use non-root user
USER www-data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Expose port
EXPOSE 5000

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "dynipv6_service:app"]
