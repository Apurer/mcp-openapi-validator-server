# Stage 2: Python Builder - Install Python and dependencies
FROM python:3.10-slim AS python-builder
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Final image based on Python base
FROM python:3.10-slim

# Copy Python dependencies from the Python builder stage
COPY --from=python-builder /usr/local/lib/python3.10 /usr/local/lib/python3.10
COPY --from=python-builder /usr/local/bin /usr/local/bin


# Set the working directory and copy the Python application
WORKDIR /app
COPY . .

# Set the entrypoint to run the Python application
ENTRYPOINT ["python3.10", "server.py"]
CMD []