"""
YouTube API Client
Handles communication with YouTube Data API v3
"""

import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class YouTubeSearchClient:
    """Client for YouTube Data API v3"""
    
    def __init__(self, api_key):
        """Initialize YouTube API client"""
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)
    
    def search_videos(self, query, max_results=25, order='relevance'):
        """
        Search for videos using YouTube API
        
        Args:
            query (str): Search query
            max_results (int): Maximum number of results to return
            order (str): Sort order ('relevance', 'date', 'viewCount', 'rating')
            
        Returns:
            list: List of video data dictionaries
        """
        try:
            # Perform search request
            search_response = self.youtube.search().list(
                q=query,
                part='id,snippet',
                type='video',
                maxResults=max_results,
                order=order
            ).execute()
            
            videos = []
            video_ids = []
            
            # Extract video IDs and basic info
            for search_result in search_response.get('items', []):
                video_id = search_result['id']['videoId']
                video_ids.append(video_id)
                
                video_data = {
                    'video_id': video_id,
                    'title': search_result['snippet']['title'],
                    'channel': search_result['snippet']['channelTitle'],
                    'description': search_result['snippet']['description'][:200] + '...' if len(search_result['snippet']['description']) > 200 else search_result['snippet']['description'],
                    'published_at': search_result['snippet']['publishedAt'],
                    'thumbnail': search_result['snippet']['thumbnails'].get('medium', {}).get('url', ''),
                    'url': f"https://www.youtube.com/watch?v={video_id}"
                }
                videos.append(video_data)
            
            # Get additional video statistics
            if video_ids:
                self._add_video_statistics(videos, video_ids)
            
            logger.info(f"Found {len(videos)} videos for query: {query}")
            return videos
            
        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
            raise Exception(f"YouTube API error: {e}")
        except Exception as e:
            logger.error(f"Search error: {e}")
            raise Exception(f"Search error: {e}")
    
    def _add_video_statistics(self, videos, video_ids):
        """Add view count and other statistics to video data"""
        try:
            # Get video statistics
            stats_response = self.youtube.videos().list(
                part='statistics,contentDetails',
                id=','.join(video_ids)
            ).execute()
            
            # Create mapping of video_id to statistics
            stats_map = {}
            for item in stats_response.get('items', []):
                stats_map[item['id']] = item
            
            # Add statistics to video data
            for video in videos:
                video_id = video['video_id']
                if video_id in stats_map:
                    stats = stats_map[video_id].get('statistics', {})
                    content_details = stats_map[video_id].get('contentDetails', {})
                    
                    video['view_count'] = int(stats.get('viewCount', 0))
                    video['like_count'] = int(stats.get('likeCount', 0))
                    video['comment_count'] = int(stats.get('commentCount', 0))
                    video['duration'] = content_details.get('duration', 'PT0M0S')
                    
        except Exception as e:
            logger.warning(f"Failed to add video statistics: {e}")
    
    def get_video_details(self, video_id):
        """Get detailed information about a specific video"""
        try:
            response = self.youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=video_id
            ).execute()
            
            if not response.get('items'):
                return None
            
            video = response['items'][0]
            snippet = video['snippet']
            statistics = video.get('statistics', {})
            content_details = video.get('contentDetails', {})
            
            return {
                'video_id': video_id,
                'title': snippet['title'],
                'channel': snippet['channelTitle'],
                'description': snippet['description'],
                'published_at': snippet['publishedAt'],
                'thumbnail': snippet['thumbnails'].get('maxres', {}).get('url', ''),
                'view_count': int(statistics.get('viewCount', 0)),
                'like_count': int(statistics.get('likeCount', 0)),
                'comment_count': int(statistics.get('commentCount', 0)),
                'duration': content_details.get('duration', 'PT0M0S'),
                'tags': snippet.get('tags', []),
                'category_id': snippet.get('categoryId', ''),
                'url': f"https://www.youtube.com/watch?v={video_id}"
            }
            
        except Exception as e:
            logger.error(f"Failed to get video details for {video_id}: {e}")
            return None
    
    def get_channel_info(self, channel_id):
        """Get information about a YouTube channel"""
        try:
            response = self.youtube.channels().list(
                part='snippet,statistics',
                id=channel_id
            ).execute()
            
            if not response.get('items'):
                return None
                
            channel = response['items'][0]
            snippet = channel['snippet']
            statistics = channel.get('statistics', {})
            
            return {
                'channel_id': channel_id,
                'title': snippet['title'],
                'description': snippet['description'],
                'subscriber_count': int(statistics.get('subscriberCount', 0)),
                'video_count': int(statistics.get('videoCount', 0)),
                'view_count': int(statistics.get('viewCount', 0)),
                'thumbnail': snippet['thumbnails'].get('medium', {}).get('url', '')
            }
            
        except Exception as e:
            logger.error(f"Failed to get channel info for {channel_id}: {e}")
            return None