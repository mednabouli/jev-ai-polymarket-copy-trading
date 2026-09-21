# Contributing to Jev AI

Thank you for considering contributing to Jev AI! This document outlines how to contribute effectively.

## Quick Links

- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Requests](#pull-requests)

## Development Setup

### Prerequisites

- Python 3.11+
- uv (recommended) or pip
- Docker & Docker Compose (for full-stack testing)
- PostgreSQL 17 (for local database testing)

### Local Development

```bash
# Clone repository
git clone https://github.com/mednabouli/jev-ai-polymarket-copy-trading.git
cd jev-ai-polymarket-copy-trading

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
cd jev-ai
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest tests/ -v
```

### Docker Development

```bash
# Build all services
docker compose build

# Run with logs
docker compose up -d
docker compose logs -f jev-ai
```

## Code Style

- **Imports**: Standard library → third-party → local (separated by blank lines)
- **Formatting**: 4-space indentation, max 100 character lines
- **Type hints**: Use for all public functions and methods
- **Docstrings**: Google style for modules, classes, and public methods
- **Logging**: Use structlog for structured JSON logging

### Example

```python
"""Module docstring describing purpose."""

import asyncio
from typing import Optional

import httpx

from config import settings


class Example:
    """Class docstring."""
    
    async def process(self, data: dict) -> Optional[str]:
        """Process data and return result.
        
        Args:
            data: Input data dictionary.
            
        Returns:
            Processed result or None if failed.
        """
        pass
```

## Testing

### Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=. --cov-report=html

# Specific test file
pytest tests/test_wallet_tracker.py -v
```

### Writing Tests

- Use pytest fixtures for common setup
- Mock external dependencies (HTTP, database, Telegram)
- Test edge cases and error conditions
- Aim for >80% code coverage

### Example Test

```python
import pytest
from wallet_tracker import WalletTracker


def test_wallet_rejected_for_low_pnl(tracker, sample_wallet):
    sample_wallet["pnl_usd"] = 5_000  # Below 10k threshold
    assert tracker._wallet_qualifies(sample_wallet) is False
```

## Pull Requests

### Before Submitting

1. Run tests: `pytest tests/ -v`
2. Check imports: `python -c "import main"`
3. Update documentation if behavior changes
4. Add tests for new features

### PR Template

```markdown
## Description
Brief summary of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe how you tested these changes.

## Checklist
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
```

## Questions?

Open an issue or reach out via Telegram @jev_ai_support.
