import os
import json
import requests
from typing import Optional, Dict, Any
from backend.config import settings
import logging

logger = logging.getLogger(__name__)


class GoogleOAuthHandler:
    """Handle Google OAuth 2.0 authentication flow."""
    
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    def __init__(self):
        self.client_id = settings.GOOGLE_OAUTH_CLIENT_ID
        self.client_secret = settings.GOOGLE_OAUTH_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI
    
    def get_auth_url(self, state: str) -> str:
        """Generate Google OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent"
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.GOOGLE_AUTH_URL}?{query_string}"
    
    def exchange_code_for_token(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token."""
        try:
            payload = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri
            }
            
            response = requests.post(self.GOOGLE_TOKEN_URL, data=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error exchanging code for token: {e}")
            return None
    
    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from Google using access token."""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(self.GOOGLE_USERINFO_URL, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None
    
    def authenticate_user(self, code: str) -> Optional[Dict[str, Any]]:
        """Complete OAuth flow and return user information."""
        token_response = self.exchange_code_for_token(code)
        if not token_response:
            return None
        
        access_token = token_response.get("access_token")
        if not access_token:
            return None
        
        user_info = self.get_user_info(access_token)
        if user_info:
            user_info["access_token"] = access_token
            user_info["refresh_token"] = token_response.get("refresh_token")
        
        return user_info
