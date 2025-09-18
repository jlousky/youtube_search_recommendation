# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Development Commands

### Setup
```bash
# Create virtual environment and install dependencies
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your YouTube API key
```

### Running the Application
```bash
# Run the Flask application
python src/main.py

# Or using Flask CLI
export FLASK_APP=src/main.py
flask run --host=0.0.0.0 --port=5000
```

### Testing
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_main.py

# Run tests with verbose output
pytest -v

# Run single test method
pytest tests/test_main.py::TestYouTubeSearchEngine::test_duration_parsing
```

### Code Quality
```bash
# Format code with Black
black src/ tests/ config/

# Lint with flake8
flake8 src/ tests/ config/

# Check specific file
black src/main.py
flake8 src/main.py
```

## Architecture Overview

This is a **personalized YouTube search engine** built with Flask that learns from user preferences to deliver more relevant search results over time.

### Core Components

**PersonalizedSearchEngine** (`src/search_engine.py`)
- Central orchestrator that combines YouTube API results with user preferences
- Handles ranking, filtering, and personalization logic
- Calculates preference scores based on channels, categories, keywords, duration, etc.
- Methods: `search()`, `get_recommendations()`, `get_trending_personalized()`

**YouTubeSearchClient** (`src/youtube_api.py`)
- Wrapper around YouTube Data API v3
- Handles video search, statistics retrieval, and channel information
- Returns structured video data with metadata (views, duration, thumbnails)
- Methods: `search_videos()`, `get_video_details()`, `get_channel_info()`

**UserPreferenceEngine** (`src/user_preferences.py`)
- Machine learning component that adapts to user behavior
- Stores preferences and interaction data in SQLite database
- Learns from clicks, likes, watch time to update preferences automatically
- Manages preferred channels, keywords, duration ranges, excluded content

**Flask Web Application** (`src/main.py`)
- Single-file Flask app with embedded HTML template
- API endpoints: `/api/search`, `/api/preferences`, `/health`
- Web interface for searching and viewing results

### Key Design Patterns

**Personalization Pipeline**: Raw YouTube results → Preference Filters → Ranking Algorithm → Personalized Results

**Learning Loop**: User Interactions → Preference Updates → Improved Future Results

**Configuration Management**: Environment-based config with development/production modes

### Database Schema

The application uses SQLite with three main tables:
- `user_preferences`: Key-value store for user settings
- `user_interactions`: Records of user actions (clicks, likes, watches)
- `search_history`: Log of search queries and results

### API Integration

YouTube Data API v3 integration requires:
- Valid API key in `YOUTUBE_API_KEY` environment variable
- Quota management (default limits to 50 results per search)
- Handles rate limiting and API errors gracefully

### Machine Learning Approach

Simple preference learning algorithm:
- Tracks positive interactions (clicks, likes, watches)
- Extracts features: channels, keywords, duration, categories
- Updates preferences incrementally
- Applies learned preferences to ranking algorithm

## Development Notes

### YouTube API Considerations
- API quota limits require careful result batching
- Duration parsing uses ISO 8601 format (`PT5M30S` = 5min 30sec)
- Video statistics require separate API call after search
- Channel information may not always be available

### Testing Strategy
- Uses pytest with mocked YouTube API for unit tests
- In-memory SQLite database (`:memory:`) for preference engine tests
- Focus on testing core algorithms (duration parsing, preference scoring)
- Integration tests require valid API key

### Environment Configuration
- Development: Debug mode enabled, verbose logging
- Production: Debug disabled, warning-level logging only
- All sensitive data managed through environment variables

### Database Considerations
- SQLite suitable for single-user development/demo
- Production deployment should consider PostgreSQL migration
- Database auto-initializes on first run
- No migrations system implemented yet