# Use official Python slim image
FROM python:3.11-slim

# Set workdir
WORKDIR /

# Copy source
COPY Microclimate_sim.py /Microclimate_sim.py
COPY requirements.txt /requirements.txt

# Install runtime dependencies (none) and dev deps for tests
RUN pip install --no-cache-dir -r requirements.txt

# Default command: run simulator indefinitely

CMD ["python", "Microclimate_sim.py", "--logfile", "/microclimate_log.csv"]

