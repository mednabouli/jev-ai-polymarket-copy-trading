FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install aiogram and dependencies
RUN pip install --no-cache-dir \
    aiogram==3.10.0 \
    aiohttp==3.10.5 \
    asyncpg==0.29.0 \
    python-dotenv==1.0.1 \
    pydantic==2.8.2 \
    structlog==24.4.0 \
    mcp==1.0.0

# Copy Telegram MCP server code
COPY server.py .

# Expose MCP server port
EXPOSE 8765

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8765/health || exit 1

# Run the MCP server
CMD ["python", "server.py"]
