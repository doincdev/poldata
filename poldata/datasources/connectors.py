import abc
import json
import hashlib
import requests
from typing import Dict, Any, Optional
from pathlib import Path
import tweepy
import facebook
from instagram_private_api import Client
from bs4 import BeautifulSoup
from ratelimit import limits, sleep_and_retry
from django.conf import settings

class BaseConnector(abc.ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.setup()

    @abc.abstractmethod
    def setup(self):
        """Initialize any necessary clients or configurations"""
        pass

    @abc.abstractmethod
    def test_connection(self) -> bool:
        """Test the connection to the data source"""
        pass

    @abc.abstractmethod
    def collect_data(self) -> Dict[str, Any]:
        """Collect data from the source"""
        pass

    def validate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Basic data validation, can be overridden by subclasses"""
        return {
            'is_valid': bool(data),
            'errors': None if bool(data) else 'Empty data'
        }

    def generate_content_hash(self, content: str) -> str:
        """Generate a hash for content deduplication"""
        return hashlib.sha256(content.encode()).hexdigest()

@sleep_and_retry
@limits(calls=15, period=900)  # 15 calls per 15 minutes
class TwitterConnector(BaseConnector):
    def setup(self):
        self.client = tweepy.Client(
            bearer_token=self.config.get('bearer_token'),
            consumer_key=self.config.get('api_key'),
            consumer_secret=self.config.get('api_secret'),
            access_token=self.config.get('access_token'),
            access_token_secret=self.config.get('access_token_secret')
        )

    def test_connection(self) -> bool:
        try:
            self.client.get_me()
            return True
        except Exception:
            return False

    def collect_data(self) -> Dict[str, Any]:
        query = self.config.get('search_query', '')
        max_results = self.config.get('max_results', 100)
        
        tweets = self.client.search_recent_tweets(
            query=query,
            max_results=max_results,
            tweet_fields=['created_at', 'public_metrics', 'source']
        )
        
        return {
            'tweets': [tweet.data for tweet in tweets.data] if tweets.data else [],
            'metadata': {
                'query': query,
                'count': len(tweets.data) if tweets.data else 0
            }
        }

@sleep_and_retry
@limits(calls=200, period=3600)  # 200 calls per hour
class FacebookConnector(BaseConnector):
    def setup(self):
        self.client = facebook.GraphAPI(
            access_token=self.config.get('access_token'),
            version=self.config.get('api_version', 'v12.0')  # Note: version string must start with 'v'
        )

    def test_connection(self) -> bool:
        try:
            self.client.get_object('me')
            return True
        except Exception:
            return False

    def collect_data(self) -> Dict[str, Any]:
        page_id = self.config.get('page_id')
        limit = self.config.get('limit', 100)
        
        posts = self.client.get_connections(
            page_id,
            'posts',
            fields='id,message,created_time,shares,reactions.summary(true)',
            limit=limit
        )
        
        return {
            'posts': list(posts['data']),
            'metadata': {
                'page_id': page_id,
                'count': len(posts['data'])
            }
        }

@sleep_and_retry
@limits(calls=200, period=3600)
class InstagramConnector(BaseConnector):
    def setup(self):
        self.client = Client(
            username=self.config.get('username'),
            password=self.config.get('password')
        )

    def test_connection(self) -> bool:
        try:
            self.client.login()
            return True
        except Exception:
            return False

    def collect_data(self) -> Dict[str, Any]:
        username = self.config.get('target_username')
        max_posts = self.config.get('max_posts', 50)
        
        user_id = self.client.username_info(username)['user']['pk']
        posts = self.client.user_feed(user_id)
        
        return {
            'posts': posts['items'][:max_posts],
            'metadata': {
                'username': username,
                'count': len(posts['items'][:max_posts])
            }
        }

@sleep_and_retry
@limits(calls=60, period=60)  # 60 calls per minute
class NewsConnector(BaseConnector):
    def setup(self):
        self.session = requests.Session()
        if self.config.get('use_proxy'):
            self.session.proxies = {
                'http': self.config.get('proxy_url'),
                'https': self.config.get('proxy_url')
            }

    def test_connection(self) -> bool:
        try:
            url = self.config.get('test_url', self.config.get('base_url'))
            response = self.session.get(url, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def collect_data(self) -> Dict[str, Any]:
        url = self.config.get('base_url')
        selectors = self.config.get('selectors', {})
        
        response = self.session.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        articles = []
        for article in soup.select(selectors.get('article_selector', 'article')):
            articles.append({
                'title': article.select_one(selectors.get('title_selector', 'h1')).text.strip(),
                'content': article.select_one(selectors.get('content_selector', 'p')).text.strip(),
                'url': article.select_one(selectors.get('link_selector', 'a'))['href'],
                'published_at': article.select_one(selectors.get('date_selector', 'time'))['datetime']
            })
        
        return {
            'articles': articles,
            'metadata': {
                'source_url': url,
                'count': len(articles)
            }
        }

class OfflineConnector(BaseConnector):
    def setup(self):
        self.file_path = Path(self.config.get('file_path', ''))

    def test_connection(self) -> bool:
        return self.file_path.exists() and self.file_path.is_file()

    def collect_data(self) -> Dict[str, Any]:
        if self.file_path.suffix.lower() == '.json':
            with open(self.file_path) as f:
                data = json.load(f)
        elif self.file_path.suffix.lower() == '.csv':
            import pandas as pd
            df = pd.read_csv(self.file_path)
            data = df.to_dict('records')
        else:
            raise ValueError(f"Unsupported file type: {self.file_path.suffix}")
        
        return {
            'records': data,
            'metadata': {
                'file_path': str(self.file_path),
                'file_type': self.file_path.suffix.lower(),
                'count': len(data)
            }
        }

def get_connector_for_source(datasource) -> BaseConnector:
    """Factory function to get the appropriate connector for a data source"""
    CONNECTOR_MAPPING = {
        'twitter': TwitterConnector,
        'facebook': FacebookConnector,
        'instagram': InstagramConnector,
        'news': NewsConnector,
        'offline': OfflineConnector,
    }
    
    connector_class = CONNECTOR_MAPPING.get(datasource.source_type)
    if not connector_class:
        raise ValueError(f"No connector available for source type: {datasource.source_type}")
    
    return connector_class(datasource.config)
