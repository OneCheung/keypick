# KeyPick

Multi-agent platform for social media content crawling and insight analysis.

## Overview

KeyPick is a cloud-native platform that leverages Dify for workflow orchestration and LLM management to crawl social media content and extract meaningful insights. The system integrates MediaCrawler for data collection and uses multiple cloud services for scalability and reliability.

## Features

- **Multi-Platform Support**: Crawl content from XiaoHongShu, Weibo, and Douyin
- **Dify Integration**: Visual workflow orchestration and LLM management
- **Cloud-Native Architecture**: Leverages Supabase, Langfuse, and other cloud services
- **Real-time Processing**: Async task processing with real-time status updates
- **LLM Observability**: Track and evaluate LLM performance with Langfuse
- **RESTful API**: Easy integration with external systems

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager (20x faster than pip)
- Redis (optional, for caching)
- Cloud service accounts:
  - Dify Cloud Pro ($49/month) - For workflow orchestration
  - Supabase (free tier) - For database storage
  - Langfuse (free tier) - For LLM observability (optional)

### Installation with uv (Recommended)

1. Clone the repository with submodules:
```bash
git clone --recurse-submodules https://github.com/yourusername/keypick.git
cd keypick
```

2. Install uv (if not already installed):
```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

3. Create virtual environment and install dependencies:
```bash
# Create virtual environment with Python 3.12
uv venv --python 3.12

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all dependencies (including dev dependencies)
uv pip install -e ".[dev]"
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration:
# - Set KEYPICK_API_KEYS for API authentication
# - Configure Supabase credentials (if using)
# - Set Redis URL (if using)
```

5. Run the API server:
```bash
uvicorn api.main:app --reload
```

The API will be available at `http://localhost:8000`

### Alternative: Traditional pip Installation

If you prefer using pip instead of uv:

```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install from pyproject.toml
pip install -e ".[dev]"

# Run the server
uvicorn api.main:app --reload
```

### Using Docker

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f api
```

## API Documentation

When running in development mode, interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Key Endpoints

- `POST /api/crawl/`: Start a crawl task
- `GET /api/crawl/status/{task_id}`: Check task status
- `GET /api/crawl/platforms`: List supported platforms
- `POST /api/process/clean`: Clean and normalize data
- `POST /api/process/extract`: Extract insights from data
- `POST /api/tools/dify/crawl`: Dify-compatible tool endpoint

## Dify Integration

### Setting up Dify Workflow

1. Log into your Dify Cloud account
2. Create a new workflow
3. Add HTTP Request node with KeyPick API endpoint
4. Configure the tool with the schema from `/api/tools/dify/schema`

### Example Dify Tool Configuration

```json
{
  "name": "keypick_crawler",
  "api_endpoint": "https://your-api.com/api/tools/dify/crawl",
  "method": "POST",
  "headers": {
    "Authorization": "Bearer YOUR_API_KEY"
  }
}
```

## Configuration

### Environment Variables

See `.env.example` for all available configuration options. Key settings:

- `KEYPICK_API_KEYS`: API keys for authenticating requests to KeyPick (comma-separated)
- `SUPABASE_URL`: Supabase project URL (optional)
- `SUPABASE_ANON_KEY`: Supabase anonymous key (optional)
- `REDIS_URL`: Redis connection string (optional, defaults to localhost)

### Supabase Setup

1. Create a new Supabase project
2. Run the following SQL to create tables:

```sql
-- Tasks table
CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  description TEXT,
  platforms JSONB,
  keywords JSONB,
  status VARCHAR(50) DEFAULT 'pending',
  config JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  progress INTEGER DEFAULT 0,
  error TEXT
);

-- Results table
CREATE TABLE results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id UUID REFERENCES tasks(id),
  platform VARCHAR(100),
  raw_data JSONB,
  processed_data JSONB,
  insights JSONB,
  report TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  item_count INTEGER DEFAULT 0,
  success BOOLEAN DEFAULT TRUE
);

-- Indexes
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_results_task_id ON results(task_id);
```

## Development

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=api --cov-report=html

# Run specific test file
pytest tests/test_integration.py -v

# Run tests in parallel (faster)
pytest tests/ -n auto
```

See [tests/TEST_GUIDE.md](tests/TEST_GUIDE.md) for detailed testing documentation.

### Code Quality Tools

```bash
# Format code with black
black api/ tests/

# Lint with ruff (faster than flake8)
ruff check api/ tests/

# Type checking
mypy api/

# Run all quality checks
black api/ tests/ && ruff check api/ tests/ && mypy api/
```

## Architecture

```
┌─────────────────────────────────────────┐
│   Dify Cloud (Workflow & LLM Management)│
└─────────────────────────────────────────┘
                  ↓ HTTP/REST
┌─────────────────────────────────────────┐
│   KeyPick FastAPI Server                │
│   - Crawler API Endpoints               │
│   - Data Processing API                 │
│   - Dify Tool Interfaces                │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│   Data Layer                            │
│   - MediaCrawler (Submodule)            │
│   - Supabase Cloud (Database)           │
│   - Redis (Cache)                       │
└─────────────────────────────────────────┘
```

## Roadmap

- [x] Phase 0.1: Environment Setup
- [x] Phase 0.2: MVP Core Functionality
- [ ] Phase 0.3: MVP Testing & Optimization
- [ ] Phase 1: Full API Development
- [ ] Phase 2: Multi-platform Support
- [ ] Phase 3: Advanced Analytics
- [ ] Phase 4: Production Deployment

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Support

- Documentation: [docs/](docs/)
- Issues: [GitHub Issues](https://github.com/yourusername/keypick/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/keypick/discussions)

## Acknowledgments

- [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) - Social media crawling
- [Dify](https://dify.ai) - Workflow orchestration
- [Langfuse](https://langfuse.com) - LLM observability
- [Supabase](https://supabase.com) - Backend as a Service
