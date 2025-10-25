import os
from dotenv import load_dotenv
from textblob import TextBlob
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
import requests
from typing import Tuple, Union, Optional

# Load environment variables
load_dotenv()

# Download required NLTK data
try:
    nltk.data.find('vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon')

def analyze_text_local(text: str) -> dict:
    """Analyze text using local processing with TextBlob and NLTK"""
    # TextBlob analysis
    blob = TextBlob(text)
    
    # NLTK VADER analysis
    sia = SentimentIntensityAnalyzer()
    vader_scores = sia.polarity_scores(text)
    
    # Combine results
    result = {
        'sentiment': 'positive' if blob.sentiment.polarity > 0 else 'negative' if blob.sentiment.polarity < 0 else 'neutral',
        'sentiment_score': blob.sentiment.polarity,
        'subjectivity': blob.sentiment.subjectivity,
        'vader_scores': vader_scores,
    }
    
    return result

def check_url_safety(url: str) -> Tuple[bool, str]:
    """Check URL safety using VirusTotal API"""
    api_key = os.getenv('VIRUSTOTAL_API_KEY')
    if not api_key:
        return False, "VirusTotal API key not configured"
    
    try:
        # First, submit the URL for scanning
        url_id = requests.post(
            'https://www.virustotal.com/vtapi/v2/url/scan',
            data={'apikey': api_key, 'url': url}
        ).json().get('scan_id')
        
        if not url_id:
            return False, "Failed to submit URL for scanning"
        
        # Then get the report
        response = requests.get(
            'https://www.virustotal.com/vtapi/v2/url/report',
            params={'apikey': api_key, 'resource': url_id}
        ).json()
        
        if response.get('response_code') == 1:  # Valid response
            positives = response.get('positives', 0)
            total = response.get('total', 0)
            
            if positives == 0:
                return True, "URL is safe"
            else:
                return False, f"URL flagged by {positives}/{total} scanners"
        else:
            return False, "Unable to get scan results"
            
    except Exception as e:
        return False, f"Error checking URL: {str(e)}"

def get_sentiment_analysis(text: str) -> Tuple[bool, dict]:
    """Get sentiment analysis using Azure Text Analytics API if available, otherwise use local processing"""
    azure_key = os.getenv('AZURE_TEXT_ANALYTICS_KEY')
    azure_endpoint = os.getenv('AZURE_TEXT_ANALYTICS_ENDPOINT')
    
    if azure_key and azure_endpoint:
        try:
            headers = {
                "Ocp-Apim-Subscription-Key": azure_key,
                "Content-Type": "application/json"
            }
            
            data = {
                "documents": [
                    {
                        "id": "1",
                        "text": text
                    }
                ]
            }
            
            response = requests.post(
                f"{azure_endpoint}/text/analytics/v3.0/sentiment",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                sentiment_doc = result['documents'][0]
                return True, {
                    'sentiment': sentiment_doc['sentiment'],
                    'confidence_scores': sentiment_doc['confidenceScores'],
                    'source': 'azure'
                }
            else:
                # Fallback to local processing
                return True, {**analyze_text_local(text), 'source': 'local'}
                
        except Exception:
            # Fallback to local processing
            return True, {**analyze_text_local(text), 'source': 'local'}
    else:
        # Use local processing if Azure is not configured
        return True, {**analyze_text_local(text), 'source': 'local'}

def check_api_status() -> dict:
    """Check status of all APIs"""
    status = {}
    
    # Check Azure Text Analytics API
    azure_key = os.getenv('AZURE_TEXT_ANALYTICS_KEY')
    azure_endpoint = os.getenv('AZURE_TEXT_ANALYTICS_ENDPOINT')
    
    if azure_key and azure_endpoint:
        try:
            headers = {"Ocp-Apim-Subscription-Key": azure_key}
            response = requests.get(f"{azure_endpoint}/text/analytics/v3.0/languages", headers=headers)
            status['azure'] = {
                'active': response.status_code == 200,
                'status': 'Active' if response.status_code == 200 else f'Error: {response.status_code}',
                'rate_limit': response.headers.get('x-rate-limit-limit', 'Unknown'),
                'rate_remaining': response.headers.get('x-rate-limit-remaining', 'Unknown')
            }
        except Exception as e:
            status['azure'] = {
                'active': False,
                'status': f'Error: {str(e)}',
                'rate_limit': 'Unknown',
                'rate_remaining': 'Unknown'
            }
    else:
        status['azure'] = {
            'active': True,  # True because we have local fallback
            'status': 'Using local processing',
            'rate_limit': 'N/A',
            'rate_remaining': 'N/A'
        }
    
    # Check VirusTotal API
    virustotal_key = os.getenv('VIRUSTOTAL_API_KEY')
    if virustotal_key:
        try:
            response = requests.get(
                'https://www.virustotal.com/vtapi/v2/url/report',
                params={'apikey': virustotal_key, 'resource': 'https://www.google.com'}
            )
            status['virustotal'] = {
                'active': response.status_code == 200,
                'status': 'Active' if response.status_code == 200 else f'Error: {response.status_code}',
                'rate_limit': '4 requests/minute',  # VirusTotal public API limit
                'rate_remaining': 'Dynamic'
            }
        except Exception as e:
            status['virustotal'] = {
                'active': False,
                'status': f'Error: {str(e)}',
                'rate_limit': 'Unknown',
                'rate_remaining': 'Unknown'
            }
    else:
        status['virustotal'] = {
            'active': False,
            'status': 'Not Configured',
            'rate_limit': 'N/A',
            'rate_remaining': 'N/A'
        }
    
    return status