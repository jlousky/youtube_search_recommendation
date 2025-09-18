"""
User Preference Engine
Handles learning and storing user preferences for video recommendations
"""

import json
import sqlite3
import logging
from datetime import datetime
from collections import defaultdict
import os

logger = logging.getLogger(__name__)

class UserPreferenceEngine:
    """Engine for learning and applying user preferences"""
    
    def __init__(self, db_path='user_preferences.db'):
        """Initialize preference engine with database"""
        self.db_path = db_path
        self._init_database()
        
        # Default preferences
        self.default_preferences = {
            'preferred_channels': [],
            'preferred_categories': [],
            'min_duration': 0,  # seconds
            'max_duration': 7200,  # 2 hours in seconds
            'preferred_languages': ['en'],
            'exclude_channels': [],
            'min_views': 0,
            'max_age_days': 365,  # 1 year
            'preferred_keywords': [],
            'disliked_keywords': []
        }
    
    def _init_database(self):
        """Initialize SQLite database for storing preferences and interactions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create preferences table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    preference_key TEXT UNIQUE NOT NULL,
                    preference_value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create user interactions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    query TEXT,
                    channel TEXT,
                    category TEXT,
                    duration INTEGER,
                    view_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create search history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    results_count INTEGER,
                    clicked_video_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def get_preferences(self):
        """Get current user preferences"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT preference_key, preference_value FROM user_preferences')
            rows = cursor.fetchall()
            
            preferences = self.default_preferences.copy()
            
            for key, value in rows:
                try:
                    preferences[key] = json.loads(value)
                except json.JSONDecodeError:
                    preferences[key] = value
            
            conn.close()
            return preferences
            
        except Exception as e:
            logger.error(f"Failed to get preferences: {e}")
            return self.default_preferences.copy()
    
    def update_preferences(self, preferences):
        """Update user preferences"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for key, value in preferences.items():
                value_json = json.dumps(value) if isinstance(value, (list, dict)) else str(value)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO user_preferences 
                    (preference_key, preference_value, updated_at)
                    VALUES (?, ?, ?)
                ''', (key, value_json, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated preferences: {list(preferences.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to update preferences: {e}")
            raise
    
    def record_interaction(self, video_data, action, query=None):
        """Record user interaction with a video"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_interactions 
                (video_id, action, query, channel, category, duration, view_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                video_data.get('video_id', ''),
                action,
                query,
                video_data.get('channel', ''),
                video_data.get('category_id', ''),
                self._parse_duration(video_data.get('duration', 'PT0M0S')),
                video_data.get('view_count', 0),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            # Update preferences based on interaction
            if action in ['clicked', 'liked', 'watched']:
                self._learn_from_interaction(video_data, action)
            
        except Exception as e:
            logger.error(f"Failed to record interaction: {e}")
    
    def _learn_from_interaction(self, video_data, action):
        """Learn user preferences from positive interactions"""
        try:
            preferences = self.get_preferences()
            
            # Learn from channel preferences
            channel = video_data.get('channel', '')
            if channel and action in ['clicked', 'liked', 'watched']:
                if channel not in preferences['preferred_channels']:
                    preferences['preferred_channels'].append(channel)
                    # Limit to top 50 preferred channels
                    if len(preferences['preferred_channels']) > 50:
                        preferences['preferred_channels'] = preferences['preferred_channels'][-50:]
            
            # Learn from category preferences
            category = video_data.get('category_id', '')
            if category and action in ['clicked', 'liked']:
                if category not in preferences['preferred_categories']:
                    preferences['preferred_categories'].append(category)
            
            # Learn from video duration preferences
            duration = self._parse_duration(video_data.get('duration', 'PT0M0S'))
            if duration > 0 and action in ['watched', 'liked']:
                # Adjust duration preferences based on watched videos
                current_min = preferences.get('min_duration', 0)
                current_max = preferences.get('max_duration', 7200)
                
                # Gradually adjust preferences towards watched content
                if duration < current_min:
                    preferences['min_duration'] = max(0, current_min - 60)
                if duration > current_max:
                    preferences['max_duration'] = min(14400, current_max + 300)  # Max 4 hours
            
            # Learn from title keywords
            title = video_data.get('title', '').lower()
            if title and action in ['clicked', 'liked']:
                # Extract potential keywords (simple approach)
                words = [word.strip('.,!?()[]') for word in title.split() if len(word) > 3]
                common_words = {'this', 'that', 'with', 'have', 'will', 'from', 'they', 'know', 
                               'want', 'been', 'good', 'much', 'some', 'time', 'very', 'when', 
                               'come', 'here', 'just', 'like', 'long', 'make', 'many', 'over', 
                               'such', 'take', 'than', 'them', 'well', 'were'}
                
                for word in words:
                    if (word not in common_words and 
                        word not in preferences['preferred_keywords'] and 
                        len(preferences['preferred_keywords']) < 100):
                        preferences['preferred_keywords'].append(word)
            
            self.update_preferences(preferences)
            
        except Exception as e:
            logger.error(f"Failed to learn from interaction: {e}")
    
    def _parse_duration(self, duration_str):
        """Parse ISO 8601 duration string to seconds"""
        try:
            # Simple parser for PT#M#S format
            if not duration_str.startswith('PT'):
                return 0
            
            duration_str = duration_str[2:]  # Remove 'PT'
            total_seconds = 0
            
            # Parse hours
            if 'H' in duration_str:
                hours, duration_str = duration_str.split('H', 1)
                total_seconds += int(hours) * 3600
            
            # Parse minutes
            if 'M' in duration_str:
                minutes, duration_str = duration_str.split('M', 1)
                total_seconds += int(minutes) * 60
            
            # Parse seconds
            if 'S' in duration_str:
                seconds = duration_str.split('S')[0]
                total_seconds += int(seconds)
            
            return total_seconds
            
        except Exception:
            return 0
    
    def record_search(self, query, results_count, clicked_video_id=None):
        """Record search query and results"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO search_history 
                (query, results_count, clicked_video_id, created_at)
                VALUES (?, ?, ?, ?)
            ''', (query, results_count, clicked_video_id, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to record search: {e}")
    
    def get_search_history(self, limit=50):
        """Get recent search history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT query, results_count, clicked_video_id, created_at
                FROM search_history
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [{'query': row[0], 'results_count': row[1], 
                    'clicked_video_id': row[2], 'created_at': row[3]} 
                   for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get search history: {e}")
            return []
    
    def get_interaction_stats(self):
        """Get statistics about user interactions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get action counts
            cursor.execute('''
                SELECT action, COUNT(*) 
                FROM user_interactions 
                GROUP BY action
            ''')
            action_counts = dict(cursor.fetchall())
            
            # Get top channels
            cursor.execute('''
                SELECT channel, COUNT(*) 
                FROM user_interactions 
                WHERE action IN ('clicked', 'liked', 'watched')
                GROUP BY channel
                ORDER BY COUNT(*) DESC
                LIMIT 10
            ''')
            top_channels = cursor.fetchall()
            
            conn.close()
            
            return {
                'action_counts': action_counts,
                'top_channels': top_channels
            }
            
        except Exception as e:
            logger.error(f"Failed to get interaction stats: {e}")
            return {'action_counts': {}, 'top_channels': []}