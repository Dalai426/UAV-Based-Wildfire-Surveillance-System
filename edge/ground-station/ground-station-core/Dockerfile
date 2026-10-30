# Small Python runtime image.
FROM python:3.13-slim

# All application files live here inside the container.
WORKDIR /app

# Copy dependencies separately so Docker can cache this layer.
COPY requirements.txt .

# Install Python dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source.
COPY app ./app

# Start the Ground Station Core HTTP API.
#
# 0.0.0.0 is required so other containers and the host
# can reach the service.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
