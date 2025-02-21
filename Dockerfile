FROM python:3.11-slim

WORKDIR /app

# Copy the entire project into the container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set the PYTHONPATH to include the app directory
ENV PYTHONPATH=/app

# Expose port for FastAPI
EXPOSE 6500

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "6500"]
