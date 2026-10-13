FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpoppler-cpp-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install API and application dependencies directly
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pydantic \
    qdrant-client \
    google-genai \
    boto3 \
    python-dotenv \ 
    loguru \
    google-generativeai \
    tenacity

# Copy application code
COPY ./api .

# Create logs directory
RUN mkdir -p logs

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]