import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib
import json
from urllib.parse import urlparse
import pandas as pd
from bs4 import BeautifulSoup
import requests

logger = logging.getLogger('datasources')

def validate_data_item(data_item):
    # Placeholder for data validation logic
    # Example: Check for required fields presence
    required_fields = ['id', 'text']
    if not all(field in data_item for field in required_fields):
        return False, "Missing required fields"
    # Additional validation rules can be added here
    return True, ""

def process_data_item(data_item):
    # Placeholder for initial processing logic (e.g. clean text, normalize, enrich)
    processed = data_item.copy()
    # Example: Convert timestamps to ISO format, remove unwanted chars etc.
    return processed

def validate_url(url: str) -> bool:
    """Validate if a given string is a valid URL."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

def sanitize_text(text: str) -> str:
    """Remove unwanted characters and normalize text."""
    if not text:
        return ""
    # Remove HTML tags
    text = BeautifulSoup(text, "html.parser").get_text()
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,!?-]', '', text)
    return text

def extract_text_from_html(html_content: str) -> str:
    """Extract meaningful text from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    return sanitize_text(soup.get_text())

def generate_content_hash(content: Any) -> str:
    """Generate a hash for content deduplication."""
    if isinstance(content, (dict, list)):
        content = json.dumps(content, sort_keys=True)
    elif not isinstance(content, str):
        content = str(content)
    return hashlib.sha256(content.encode()).hexdigest()

def validate_date_format(date_str: str) -> bool:
    """Validate if a string is in a recognized date format."""
    date_formats = [
        '%Y-%m-%d',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%fZ'
    ]
    
    for fmt in date_formats:
        try:
            datetime.strptime(date_str, fmt)
            return True
        except ValueError:
            continue
    return False

def preprocess_social_media_text(text: str) -> str:
    """Preprocess social media text content."""
    # Convert to lowercase
    text = text.lower()
    # Remove URLs
    text = re.sub(r'http\S+|www.\S+', '', text)
    # Remove mentions (@username)
    text = re.sub(r'@\w+', '', text)
    # Remove hashtags but keep the text
    text = re.sub(r'#(\w+)', r'\1', text)
    # Remove emojis and special characters
    text = re.sub(r'[^\w\s.,!?-]', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_metadata_from_url(url: str) -> Dict[str, Any]:
    """Extract metadata from a URL using requests and BeautifulSoup."""
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        metadata = {
            'title': soup.title.string if soup.title else None,
            'description': None,
            'image': None,
            'site_name': None,
            'author': None,
            'published_date': None
        }
        
        # Try to get OpenGraph metadata
        og_metadata = {
            'description': soup.find('meta', property='og:description'),
            'image': soup.find('meta', property='og:image'),
            'site_name': soup.find('meta', property='og:site_name')
        }
        
        for key, tag in og_metadata.items():
            if tag:
                metadata[key] = tag.get('content')
        
        # Try to get other common metadata
        other_metadata = {
            'description': soup.find('meta', attrs={'name': 'description'}),
            'author': soup.find('meta', attrs={'name': 'author'}),
            'published_date': soup.find('meta', attrs={'name': 'published_date'})
        }
        
        for key, tag in other_metadata.items():
            if tag and not metadata[key]:
                metadata[key] = tag.get('content')
        
        return {k: v for k, v in metadata.items() if v}
    except Exception:
        return {}

def validate_json_structure(data: Dict[str, Any], required_fields: List[str]) -> tuple[bool, Optional[str]]:
    """Validate JSON structure against required fields."""
    if not isinstance(data, dict):
        return False, "Data must be a dictionary"
    
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    return True, None

def normalize_collected_data(data: Dict[str, Any], source_type: str) -> Dict[str, Any]:
    """Normalize collected data into a standard format based on source type."""
    normalized = {
        'content': None,
        'metadata': {},
        'timestamp': datetime.now().isoformat(),
        'source_type': source_type
    }
    
    if source_type == 'twitter':
        if 'tweets' in data:
            tweets_data = []
            for tweet in data['tweets']:
                tweet_content = {
                    'id': tweet.get('id'),
                    'text': preprocess_social_media_text(tweet.get('text', '')),
                    'created_at': tweet.get('created_at'),
                    'metrics': tweet.get('public_metrics', {})
                }
                tweets_data.append(tweet_content)
            normalized['content'] = tweets_data
            
    elif source_type == 'news':
        if 'articles' in data:
            articles_data = []
            for article in data['articles']:
                article_content = {
                    'title': sanitize_text(article.get('title', '')),
                    'content': sanitize_text(article.get('content', '')),
                    'url': article.get('url'),
                    'published_at': article.get('published_at')
                }
                articles_data.append(article_content)
            normalized['content'] = articles_data
            
    elif source_type == 'offline':
        if 'records' in data:
            normalized['content'] = pd.json_normalize(data['records']).to_dict(orient='records')
    
    # Add metadata from the original data
    if 'metadata' in data:
        normalized['metadata'] = data['metadata']
    
    return normalized

def calculate_credibility_score(data: Dict[str, Any], source_type: str) -> float:
    """Calculate credibility score based on various factors."""
    score = 50.0  # Start with neutral score
    
    if source_type == 'twitter':
        # Check for verified status
        if data.get('verified', False):
            score += 10
        # Check engagement metrics
        metrics = data.get('public_metrics', {})
        if metrics:
            followers = metrics.get('followers_count', 0)
            if followers > 10000:
                score += 10
            elif followers > 1000:
                score += 5
    
    elif source_type == 'news':
        # Check if it's from a known domain
        url = data.get('url', '')
        if url:
            domain = urlparse(url).netloc
            # Add your trusted domains logic here
            trusted_domains = {'example.com', 'trusted-news.com'}
            if domain in trusted_domains:
                score += 20
        
        # Check content length and structure
        content = data.get('content', '')
        if content:
            words = len(content.split())
            if words > 300:
                score += 10
            if re.search(r'\b(source|according to)\b', content.lower()):
                score += 5
    
    # Normalize score to 0-100 range
    return max(0, min(100, score))
