"""
Personalized Search Engine
Combines YouTube API with user preferences for personalized search results
"""

import logging
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

class PersonalizedSearchEngine:
    """Main search engine that personalizes results based on user preferences"""
    
    def __init__(self, youtube_client, preference_engine):
        """Initialize search engine with YouTube client and preference engine"""
        self.youtube_client = youtube_client
        self.preference_engine = preference_engine
    
    def search(self, query, max_results=25):
        """
        Perform personalized search
        
        Args:
            query (str): Search query
            max_results (int): Maximum number of results to return
            
        Returns:
            list: Personalized and ranked video results
        """
        try:
            # Get raw results from YouTube API
            raw_results = self.youtube_client.search_videos(
                query=query,
                max_results=min(max_results * 2, 50),  # Get more results for filtering
                order='relevance'
            )
            
            # Get user preferences
            preferences = self.preference_engine.get_preferences()
            
            # Apply personalization filters
            filtered_results = self._apply_preference_filters(raw_results, preferences)
            
            # Rank results based on preferences
            ranked_results = self._rank_by_preferences(filtered_results, preferences, query)
            
            # Limit to requested number of results
            final_results = ranked_results[:max_results]
            
            # Record search in history
            self.preference_engine.record_search(
                query=query,
                results_count=len(final_results)
            )
            
            logger.info(f"Search '{query}' returned {len(final_results)} personalized results")
            return final_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def _apply_preference_filters(self, videos, preferences):
        """Apply user preference filters to video results"""
        filtered_videos = []
        
        for video in videos:
            # Skip if channel is in exclude list
            if video.get('channel', '') in preferences.get('exclude_channels', []):
                continue
            
            # Filter by duration
            duration = self._parse_duration(video.get('duration', 'PT0M0S'))
            min_duration = preferences.get('min_duration', 0)
            max_duration = preferences.get('max_duration', 7200)
            
            if duration < min_duration or duration > max_duration:
                continue
            
            # Filter by minimum views
            min_views = preferences.get('min_views', 0)
            if video.get('view_count', 0) < min_views:
                continue
            
            # Filter by age
            max_age_days = preferences.get('max_age_days', 365)
            if self._is_video_too_old(video.get('published_at', ''), max_age_days):
                continue
            
            # Filter by disliked keywords
            disliked_keywords = preferences.get('disliked_keywords', [])
            title_lower = video.get('title', '').lower()
            description_lower = video.get('description', '').lower()
            
            if any(keyword.lower() in title_lower or keyword.lower() in description_lower 
                   for keyword in disliked_keywords):
                continue
            
            filtered_videos.append(video)
        
        return filtered_videos
    
    def _rank_by_preferences(self, videos, preferences, query):
        """Rank videos based on user preferences"""
        scored_videos = []
        
        for video in videos:
            score = self._calculate_preference_score(video, preferences, query)
            scored_videos.append((score, video))
        
        # Sort by score (descending)
        scored_videos.sort(key=lambda x: x[0], reverse=True)
        
        # Return just the videos (without scores)
        return [video for score, video in scored_videos]
    
    def _calculate_preference_score(self, video, preferences, query):
        """Calculate preference score for a video"""
        score = 0.0
        
        # Base relevance score (YouTube's relevance ranking)
        score += 1.0
        
        # Channel preference boost
        preferred_channels = preferences.get('preferred_channels', [])
        if video.get('channel', '') in preferred_channels:
            score += 2.0
        
        # Category preference boost
        preferred_categories = preferences.get('preferred_categories', [])
        if video.get('category_id', '') in preferred_categories:
            score += 1.5
        
        # Keyword preference boost
        preferred_keywords = preferences.get('preferred_keywords', [])
        title_lower = video.get('title', '').lower()
        description_lower = video.get('description', '').lower()
        
        keyword_matches = 0
        for keyword in preferred_keywords:
            if (keyword.lower() in title_lower or 
                keyword.lower() in description_lower):
                keyword_matches += 1
        
        score += keyword_matches * 0.5
        
        # Query relevance boost
        query_words = query.lower().split()
        query_matches = 0
        for word in query_words:
            if word in title_lower:
                query_matches += 1
        
        if query_words:
            query_relevance = query_matches / len(query_words)
            score += query_relevance * 2.0
        
        # View count normalization (log scale to prevent domination)
        view_count = video.get('view_count', 0)
        if view_count > 0:
            import math
            score += math.log10(view_count) * 0.1
        
        # Like ratio boost (if like count available)
        like_count = video.get('like_count', 0)
        if like_count > 0 and view_count > 0:
            like_ratio = like_count / view_count
            score += like_ratio * 100  # Scale up since ratio is very small
        
        # Recency boost for newer videos
        days_old = self._get_video_age_days(video.get('published_at', ''))
        if days_old >= 0:
            # Boost newer videos (decay over 30 days)
            recency_boost = max(0, (30 - days_old) / 30) * 0.5
            score += recency_boost
        
        # Duration preference alignment
        duration = self._parse_duration(video.get('duration', 'PT0M0S'))
        preferred_min = preferences.get('min_duration', 0)
        preferred_max = preferences.get('max_duration', 7200)
        
        if preferred_min <= duration <= preferred_max:
            # Bonus for being in preferred duration range
            score += 0.3
        
        return score
    
    def _parse_duration(self, duration_str):
        """Parse ISO 8601 duration string to seconds"""
        try:
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
    
    def _is_video_too_old(self, published_at, max_age_days):
        """Check if video is older than maximum age preference"""
        try:
            if not published_at:
                return False
            
            # Parse ISO format datetime
            published_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            max_age = timedelta(days=max_age_days)
            
            return (datetime.now(published_date.tzinfo) - published_date) > max_age
            
        except Exception:
            return False
    
    def _get_video_age_days(self, published_at):
        """Get video age in days"""
        try:
            if not published_at:
                return -1
            
            published_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            age = datetime.now(published_date.tzinfo) - published_date
            
            return age.days
            
        except Exception:
            return -1
    
    def search_by_channel(self, channel_name, max_results=25):
        """Search videos from a specific channel"""
        try:
            query = f"channel:{channel_name}"
            return self.search(query, max_results)
            
        except Exception as e:
            logger.error(f"Channel search failed: {e}")
            return []
    
    def get_trending_personalized(self, max_results=25):
        """Get trending videos personalized to user preferences"""
        try:
            # Use generic trending queries and personalize
            trending_queries = [
                'trending today',
                'popular videos',
                'viral videos',
                'latest trending'
            ]
            
            all_results = []
            
            for query in trending_queries:
                results = self.search(query, max_results // len(trending_queries))
                all_results.extend(results)
            
            # Remove duplicates by video_id
            seen_ids = set()
            unique_results = []
            
            for video in all_results:
                video_id = video.get('video_id', '')
                if video_id not in seen_ids:
                    seen_ids.add(video_id)
                    unique_results.append(video)
            
            return unique_results[:max_results]
            
        except Exception as e:
            logger.error(f"Trending search failed: {e}")
            return []
    
    def get_recommendations(self, max_results=25):
        """Get video recommendations based on user preferences and history"""
        try:
            preferences = self.preference_engine.get_preferences()
            
            # Build recommendation queries from preferences
            queries = []
            
            # Use preferred keywords
            preferred_keywords = preferences.get('preferred_keywords', [])[:10]  # Limit to top 10
            for keyword in preferred_keywords:
                queries.append(keyword)
            
            # Use preferred channels
            preferred_channels = preferences.get('preferred_channels', [])[:5]  # Limit to top 5
            for channel in preferred_channels:
                queries.append(f"channel:{channel}")
            
            # If no preferences, use generic recommendations
            if not queries:
                queries = ['educational', 'entertainment', 'technology', 'music']
            
            all_results = []
            results_per_query = max(1, max_results // len(queries))
            
            for query in queries:
                try:
                    results = self.search(query, results_per_query)
                    all_results.extend(results)
                except Exception as e:
                    logger.warning(f"Failed to get recommendations for query '{query}': {e}")
                    continue
            
            # Remove duplicates and limit results
            seen_ids = set()
            unique_results = []
            
            for video in all_results:
                video_id = video.get('video_id', '')
                if video_id not in seen_ids:
                    seen_ids.add(video_id)
                    unique_results.append(video)
            
            return unique_results[:max_results]
            
        except Exception as e:
            logger.error(f"Recommendations failed: {e}")
            return []