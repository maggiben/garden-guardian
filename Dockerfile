# Use the official Python image from the Docker Hub
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy only the pdm configuration files first, to leverage Docker cache
COPY pyproject.toml pdm.lock* /app/

# Install pdm
RUN pip install --no-cache-dir pdm

# Install dependencies
RUN pdm install --production

# Copy the rest of the application code
COPY . /app

# Ensure pdm's virtual environment is used
ENV PATH="/app/.venv/bin:${PATH}"

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=3001

# Expose the port the app runs on
EXPOSE 3001

# Run the application
CMD ["pdm", "run", "flask", "run"]
