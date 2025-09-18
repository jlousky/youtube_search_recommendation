# YouTube Video Search Engine

A personalized YouTube video search engine that learns from user preferences to deliver more relevant search results.

## Features

- Search YouTube videos based on user queries
- Learn and adapt to user preferences over time
- Personalized ranking and filtering
- User preference management
- Search history and analytics

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd youtube-search-engine
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your YouTube API key:
```bash
export YOUTUBE_API_KEY=your_api_key_here
```

4. Run the application:
```bash
python src/main.py
```

## Configuration

Configuration files are located in the `config/` directory. Update `config/settings.py` with your preferences.

## Project Structure

```
youtube-search-engine/
├── src/                 # Source code
├── tests/               # Test files
├── docs/                # Documentation
├── config/              # Configuration files
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License