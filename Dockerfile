FROM python:3.11-slim

WORKDIR /app

# Copy requirements.txt first to leverage Docker layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY ./app/ .

# Expose the port
EXPOSE 6500

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "6500"]