FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
RUN pip install --no-cache-dir uv

# Copy pyproject.toml and install dependencies
COPY pyproject.toml .
RUN uv pip install --system -e .

# Copy MCP server code
COPY src/ ./src/

# Expose MCP server port
EXPOSE 8766

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8766/health || exit 1

# Run the MCP server
CMD ["python", "-m", "polymarket_mcp_server.main", "--host", "0.0.0.0", "--port", "8766"]
