# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**KeyPick** is a multi-agent platform for social media content crawling and insight analysis, leveraging a cloud-native architecture with Dify for workflow orchestration and LLM management.

## Architecture

The project uses a **simplified cloud-first architecture**:

```
┌─────────────────────────────────────────┐
│   Dify Cloud (Workflow & LLM Management)│
│   - Crawler Workflow                    │
│   - Analysis Agent                      │
│   - LLM Provider Configuration          │
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

## Key Technologies

- **Dify Cloud**: $49/month Pro version for workflow orchestration and LLM management
- **Langfuse Cloud**: Free tier for LLM evaluation and monitoring
- **Supabase Cloud**: Free tier for PostgreSQL database and real-time subscriptions
- **MediaCrawler**: Forked as submodule for social media crawling capabilities
- **FastAPI**: Python web framework for the KeyPick API server

## Current Project State

- MediaCrawler has been added as a Git submodule (forked version)
- Project roadmap has been defined with 8-10 week timeline
- Cloud services architecture has been chosen over self-hosted solutions
- easy-ai-proxy development is not needed (Dify handles LLM routing)

## Development Setup

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/yourusername/keypick.git
cd keypick

# Initialize submodules if needed
git submodule update --init --recursive

# Set up Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (once requirements.txt is created)
pip install -r requirements.txt
```

## Project Structure

```
keypick/
├── MediaCrawler/           # Git submodule (forked)
├── api/                    # FastAPI service
│   ├── routers/           # API endpoints
│   ├── services/          # Business logic
│   └── models/            # Data models
├── dify/                   # Dify configurations
│   ├── workflows/         # Workflow DSL files
│   └── agents/            # Agent configurations
└── tests/                  # Test suite
```

## Key Implementation Tasks

1. **FastAPI Service Development**:
   - Implement crawler API endpoints
   - Create Dify tool interfaces
   - Integrate with MediaCrawler

2. **Dify Integration**:
   - Configure crawler workflow in Dify Cloud
   - Set up analysis agent
   - Implement DSL version management

3. **Data Storage**:
   - Configure Supabase Cloud connection
   - Design database schema
   - Implement caching with Redis

## Development Commands

```bash
# Run FastAPI server (once implemented)
uvicorn api.main:app --reload

# Run tests
pytest

# Lint and format
black .
flake8 .
```

## Important Notes

- Focus on MVP features first (single platform crawling)
- Use Dify's built-in LLM management instead of developing custom routing
- Leverage cloud services to minimize infrastructure management
- Total operational cost: $54-59/month with cloud services

## References

- ROADMAP.md - Detailed project roadmap and architecture
- DEPLOYMENT_GUIDE.md - Cloud deployment strategies
- TECHNICAL_RESEARCH.md - Technical implementation details