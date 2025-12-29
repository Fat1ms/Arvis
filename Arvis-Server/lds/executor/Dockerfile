# Executor container for task execution
FROM python:3.11-slim

# Minimal base image - remove unnecessary tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /bin/sh && \
    rm -rf /usr/bin/apt-get && \
    rm -rf /usr/bin/dpkg

# Create non-root user
RUN useradd -m -u 1000 executor
USER executor

WORKDIR /app

# Copy only Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy executor script
COPY executor.py .

# No shell - direct Python execution
ENTRYPOINT ["python", "-u", "executor.py"]
