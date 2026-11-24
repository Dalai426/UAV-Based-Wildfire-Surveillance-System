# Small Python runtime image
FROM python:3.13-slim

# All application files live here inside the container
WORKDIR /app

# Copy dependencies separately so Docker can cache this layer
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source
COPY app ./app

# Create a non-root Core user in the shared data group used with Cloud Sync.
# Fixed UID/GID values keep file ownership consistent across image rebuilds.
RUN groupadd --gid 10000 gsdata \
    && useradd --uid 10001 --gid gsdata \
       --create-home --shell /usr/sbin/nologin core

USER core

# Start the Ground Station Core HTTP API
#
# 0.0.0.0 is required so other containers and the host
# can reach the service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
