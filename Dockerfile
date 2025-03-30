FROM python:3.10-slim AS python-builder
WORKDIR /app

# Copy requirements and install dependencies in a virtual environment
COPY requirements.txt .
RUN python -m venv /app/venv && \
    . /app/venv/bin/activate && \
    pip install --no-cache-dir -r requirements.txt

# Stage 3: Final image based on Python base
FROM python:3.10-slim

# Copy the virtual environment from the builder stage
COPY --from=python-builder /app/venv /app/venv

# Set the working directory and copy the Python application
WORKDIR /app
COPY . .

# Use the virtual environment's Python binary to run the application
ENTRYPOINT ["/app/venv/bin/python", "server.py"]
CMD []