#!/usr/bin/env python3
"""
YouTube Video Search Engine
Main application entry point
"""

import os
import sys
import logging
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

# Add src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import config
from youtube_api import YouTubeSearchClient
from user_preferences import UserPreferenceEngine
from search_engine import PersonalizedSearchEngine

def create_app(config_name=None):
    """Create and configure the Flask application"""
    
    app = Flask(__name__)
    CORS(app)
    
    # Load configuration
    config_name = config_name or os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # Set up logging
    logging.basicConfig(
        level=getattr(logging, app.config['LOG_LEVEL']),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting YouTube Search Engine in {config_name} mode")
    
    # Initialize components
    youtube_client = YouTubeSearchClient(app.config['YOUTUBE_API_KEY'])
    preference_engine = UserPreferenceEngine()
    search_engine = PersonalizedSearchEngine(youtube_client, preference_engine)
    
    @app.route('/')
    def index():
        """Main search interface"""
        html_template = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>YouTube Video Search Engine</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                .search-box { width: 100%; padding: 10px; margin: 10px 0; font-size: 16px; }
                .search-btn { padding: 10px 20px; background: #ff0000; color: white; border: none; cursor: pointer; }
                .video-result { border: 1px solid #ddd; margin: 10px 0; padding: 15px; }
                .video-title { font-weight: bold; color: #1a0dab; }
                .video-channel { color: #666; }
                .video-description { margin-top: 5px; }
            </style>
        </head>
        <body>
            <h1>🎥 YouTube Video Search Engine</h1>
            <p>Personalized video search based on your preferences</p>
            
            <form id="searchForm">
                <input type="text" id="searchQuery" class="search-box" placeholder="Enter your search query..." required>
                <button type="submit" class="search-btn">Search Videos</button>
            </form>
            
            <div id="results"></div>
            
            <script>
                document.getElementById('searchForm').onsubmit = function(e) {
                    e.preventDefault();
                    const query = document.getElementById('searchQuery').value;
                    searchVideos(query);
                };
                
                function searchVideos(query) {
                    fetch('/api/search?q=' + encodeURIComponent(query))
                        .then(response => response.json())
                        .then(data => displayResults(data))
                        .catch(error => console.error('Error:', error));
                }
                
                function displayResults(data) {
                    const resultsDiv = document.getElementById('results');
                    if (data.error) {
                        resultsDiv.innerHTML = '<p>Error: ' + data.error + '</p>';
                        return;
                    }
                    
                    let html = '<h2>Search Results (' + data.videos.length + ' videos found)</h2>';
                    data.videos.forEach(video => {
                        html += '<div class="video-result">';
                        html += '<div class="video-title">' + video.title + '</div>';
                        html += '<div class="video-channel">by ' + video.channel + '</div>';
                        html += '<div class="video-description">' + (video.description || '') + '</div>';
                        html += '<a href="https://youtube.com/watch?v=' + video.video_id + '" target="_blank">Watch on YouTube</a>';
                        html += '</div>';
                    });
                    resultsDiv.innerHTML = html;
                }
            </script>
        </body>
        </html>
        '''
        return render_template_string(html_template)
    
    @app.route('/api/search')
    def api_search():
        """API endpoint for video search"""
        try:
            query = request.args.get('q', '').strip()
            if not query:
                return jsonify({'error': 'Search query is required'}), 400
            
            # Perform personalized search
            results = search_engine.search(query)
            
            return jsonify({
                'query': query,
                'videos': results,
                'total': len(results)
            })
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/preferences', methods=['GET', 'POST'])
    def api_preferences():
        """API endpoint for user preferences"""
        if request.method == 'GET':
            preferences = preference_engine.get_preferences()
            return jsonify(preferences)
        
        elif request.method == 'POST':
            try:
                data = request.get_json()
                preference_engine.update_preferences(data)
                return jsonify({'message': 'Preferences updated successfully'})
            except Exception as e:
                logger.error(f"Preferences update error: {str(e)}")
                return jsonify({'error': 'Failed to update preferences'}), 500
    
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'version': '1.0.0',
            'environment': config_name
        })
    
    return app

def main():
    """Main function to run the application"""
    app = create_app()
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config['FLASK_DEBUG']
    )

if __name__ == '__main__':
    main()