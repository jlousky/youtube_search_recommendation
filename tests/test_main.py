"""
Basic tests for the YouTube Search Engine
"""

import pytest
import sys
import os

# Add src directory to Python path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestYouTubeSearchEngine:
    """Test cases for the main search engine functionality"""
    
    def test_import_modules(self):
        """Test that all main modules can be imported"""
        try:
            from main import create_app
            from youtube_api import YouTubeSearchClient
            from user_preferences import UserPreferenceEngine
            from search_engine import PersonalizedSearchEngine
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import modules: {e}")
    
    def test_create_app(self):
        """Test that Flask app can be created"""
        from main import create_app
        app = create_app('development')
        assert app is not None
        assert app.config['FLASK_DEBUG'] == True
    
    def test_preference_engine_init(self):
        """Test that UserPreferenceEngine can be initialized"""
        from user_preferences import UserPreferenceEngine
        engine = UserPreferenceEngine(':memory:')  # Use in-memory database for testing
        preferences = engine.get_preferences()
        assert isinstance(preferences, dict)
        assert 'preferred_channels' in preferences
    
    def test_duration_parsing(self):
        """Test duration parsing functionality"""
        from search_engine import PersonalizedSearchEngine
        from unittest.mock import Mock
        
        # Create mock objects
        mock_youtube = Mock()
        mock_prefs = Mock()
        
        engine = PersonalizedSearchEngine(mock_youtube, mock_prefs)
        
        # Test various duration formats
        assert engine._parse_duration('PT5M30S') == 330  # 5 minutes 30 seconds
        assert engine._parse_duration('PT1H30M') == 5400  # 1 hour 30 minutes
        assert engine._parse_duration('PT45S') == 45  # 45 seconds
        assert engine._parse_duration('PT2H') == 7200  # 2 hours
        assert engine._parse_duration('invalid') == 0  # Invalid format

if __name__ == '__main__':
    pytest.main([__file__])