# Stage 1: Build Python environment with dependencies
FROM python:3.10-slim AS python-builder
WORKDIR /app

# Copy requirements and install dependencies in a virtual environment
COPY requirements.txt .
RUN python -m venv /app/venv && \
    . /app/venv/bin/activate && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Build the openapi-style-validator CLI JAR using Gradle
FROM gradle:7.6-jdk11 AS java-builder
WORKDIR /build

# Clone the openapi-style-validator repository
RUN git clone https://github.com/OpenAPITools/openapi-style-validator.git .

# Build the JAR using the shadowJar task
RUN ./gradlew shadowJar

# Copy the built CLI jar to a known location in /build.
# Adjust the glob pattern if necessary - this looks for any jar with "cli" in its name.
RUN cp $(find . -name "*cli*.jar" | head -n 1) /build/openapi-style-validator-cli.jar

# Stage 3: Final image based on Python 3.10-slim with Java installed
FROM python:3.10-slim
WORKDIR /app

# Install Java runtime
RUN apt-get update && apt-get install -y default-jre && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the python-builder stage
COPY --from=python-builder /app/venv /app/venv

# Copy the entire application source code
COPY . .

# Create a tools directory and copy the built CLI jar from the java-builder stage
RUN mkdir -p /app/tools
COPY --from=java-builder /build/openapi-style-validator-cli.jar /app/tools/openapi-style-validator-cli.jar

# Set environment variable for the OpenAPI style validator CLI JAR file
ENV OPENAPI_STYLE_VALIDATOR_JAR=/app/tools/openapi-style-validator-cli.jar

# Use the virtual environment's Python binary to run the application
ENTRYPOINT ["/app/venv/bin/python", "server.py"]
CMD []