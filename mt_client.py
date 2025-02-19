import requests
import time
from typing import Dict, Optional, Union
from dataclasses import dataclass
import json
import os

@dataclass
class AccountInfo:
    registered: str = None
    uid: str = None
    name: str = None
    max_rank: str = None
    level: str = None
    country: str = None
    bind_email: str = None
    avatar: str = None
    other_roles: str = None

class MTResponse:
    def __init__(self, success: bool, error: Optional[str] = None, account_info: Optional[Dict] = None, data: Optional[Dict] = None):
        self.success = success
        self.error = error
        self.account_info = account_info
        self.data = data

    @property
    def info(self) -> Optional[str]:
        if not self.account_info:
            return None
        
        info_parts = []
        if uid := self.account_info.get('uid'):
            info_parts.append(f"UID: {uid}")
        if name := self.account_info.get('name'):
            info_parts.append(f"Name: {name}")
        if rank := self.account_info.get('max_rank'):
            info_parts.append(f"Rank: {rank}")
        if level := self.account_info.get('level'):
            info_parts.append(f"Level: {level}")
        if country := self.account_info.get('country'):
            info_parts.append(f"Country: {country}")
        if bind_email := self.account_info.get('bind_email'):
            info_parts.append(f"Email: {bind_email}")
        if registered := self.account_info.get('registered'):
            info_parts.append(f"Registered: {registered}")
        
        return " | ".join(info_parts) if info_parts else None

class MTClient:
    # List of backup servers to try before fetching from mtchecker.info
    BACKUP_SERVERS = [
        "https://mtchk-sg.onrender.com",
        "https://mtchk-sg-bak.onrender.com",
        "https://mtchk-m.onrender.com",
    ]
    
    def __init__(self, api_key: str, base_url: str = "https://mtfastapi.pro"):
        self.api_key = api_key
        self.base_url = base_url
        self.current_server_index = 0
        # Use os.path to get the correct config path
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36',
            'Pragma': 'no-cache',
            'Accept': '*/*',
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        })

    def _validate_password_format(self, password: str) -> tuple[bool, str, str]:
        """
        Validate password format and auto-capitalize if needed.
        
        Args:
            password (str): Password to validate
            
        Returns:
            tuple[bool, str, str]: (is_valid, modified_password, error_message)
        """
        if len(password) < 6:
            return False, password, "Password must be at least 6 characters long"
            
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)
        
        if has_special:
            return False, password, "Password should not contain special symbols"
            
        if not (has_upper and has_lower and has_digit):
            # Auto-capitalize first letter if no uppercase exists
            if not has_upper:
                for i, char in enumerate(password):
                    if char.isalpha():
                        password = password[:i] + char.upper() + password[i+1:]
                        break
            
            if not has_digit:
                return False, password, "Password must contain at least one number"
                
        return True, password, ""

    def _fetch_available_servers(self) -> list:
        """Fetch available servers from status API"""
        try:
            response = requests.get("https://mtchecker.info/status/json", timeout=10)
            data = response.json()
            # Sort servers by uptime percentage in descending order
            servers = sorted(
                [s for s in data["servers"] if s["uptime_percentage"] > 0],
                key=lambda x: x["uptime_percentage"],
                reverse=True
            )
            return servers
        except Exception as e:
            print(f"Failed to fetch servers: {e}")
            return []

    def _test_server(self, server_url: str) -> bool:
        """Test if a server is working properly by checking /ping endpoint"""
        try:
            # Add timeout to avoid hanging
            response = requests.get(f"{server_url}/ping", timeout=5)
            if "This service has been suspended" in response.text:
                return False
            try:
                data = response.json()
                return data.get("status") == "ok" and data.get("message") == "pong"
            except json.JSONDecodeError:
                return False
        except Exception:
            return False

    def _update_base_url(self, new_url: str):
        """Update base URL in config file and client"""
        try:
            if not os.path.exists(self.config_path):
                print(f"Config file not found at: {self.config_path}")
                return
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            config['base_url'] = new_url
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            self.base_url = new_url
        except Exception as e:
            print(f"Failed to update config: {e}")

    def _switch_server(self) -> bool:
        """Try to switch to a working server"""
        # First check if current server is working
        if self._test_server(self.base_url):
            return False  # Current server is fine, no need to switch
            
        # If current server is suspended, try backup servers
        for server in self.BACKUP_SERVERS:
            if server != self.base_url and self._test_server(server):
                self._update_base_url(server)
                return True
        
        # If all backup servers fail, then try mtchecker.info
        servers = self._fetch_available_servers()
        for server in servers:
            if server["name"] != self.base_url and server["name"] not in self.BACKUP_SERVERS and self._test_server(server["name"]):
                self._update_base_url(server["name"])
                return True
        
        return False

    def _make_request_with_retry(self, request_func, max_retries=3):
        """
        Execute a request with retry logic and server switching.
        
        Args:
            request_func: Function that makes the actual request
            max_retries: Maximum number of retry attempts
            
        Returns:
            Response from the request or raises the last error
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                response = request_func()
                
                # Check if response is empty or invalid
                if not response.text.strip():
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    raise requests.RequestException("Empty response received")
                
                # Check if server is suspended
                if "This service has been suspended" in response.text:
                    if self._switch_server():
                        continue  # Try again with new server
                    raise requests.RequestException("All servers are suspended")
                    
                return response
                
            except requests.RequestException as e:
                last_error = e
                error_str = str(e).lower()
                
                # Check for various timeout and connection errors
                if any(err in error_str for err in [
                    'timeout', 'timed out', 'connection error', 
                    'connection refused', 'connection reset',
                    'no route to host', 'connection aborted'
                ]):
                    if attempt < max_retries - 1:
                        time.sleep(1)  # Wait before retry
                        continue
                else:
                    # If it's not a timeout/connection error, don't retry
                    raise
        
        # If we've exhausted all retries, raise the last error
        raise last_error

    def validate_account(self, username: str, password: str, proxy: Optional[Union[str, Dict]] = None) -> MTResponse:
        """
        Validate account credentials against the MT API.
        
        Args:
            username (str): Account username
            password (str): Account password
            proxy (Union[str, Dict], optional): Proxy configuration
            
        Example payloads:
            Format 1 (With credentials):
            {
                "username": "user@example.com",
                "password": "password123",
                "proxy": {
                    "url": "proxy.example.com:8080",
                    "type": "http",
                    "username": "proxyuser",
                    "password": "proxypass"
                }
            }

            Format 2 (Without credentials):
            {
                "username": "user@example.com",
                "password": "password123",
                "proxy": {
                    "url": "proxy.example.com:8080",
                    "type": "http"
                }
            }

            Format 3 (Simple string):
            {
                "username": "user@example.com",
                "password": "password123",
                "proxy": "proxy.example.com:8080"
            }
            
        Returns:
            MTResponse: Response object containing success status and any error messages
        """
        is_valid, modified_password, error_msg = self._validate_password_format(password)
        if not is_valid:
            return MTResponse(success=False, error=error_msg)
            
        password = modified_password
        
        try:
            def make_request():
                payload = {
                    "username": username,
                    "password": password
                }
                
                # Handle proxy configuration
                if proxy:
                    if isinstance(proxy, str):
                        # Format 3: Simple string
                        payload["proxy"] = proxy
                    elif isinstance(proxy, dict):
                        # Format 1 & 2: Dict with url and type
                        proxy_data = {}
                        if "url" in proxy:
                            proxy_data["url"] = proxy["url"]
                            proxy_data["type"] = proxy.get("type", "http")
                            
                            # Add credentials if present (Format 1)
                            if proxy.get("username") and proxy.get("password"):
                                proxy_data["username"] = proxy["username"]
                                proxy_data["password"] = proxy["password"]
                                
                            payload["proxy"] = proxy_data
                        else:
                            # If no URL structure, use the proxy as is
                            payload["proxy"] = proxy

                # Print payload for debugging
                # print(f"\nValidate Request Payload: {json.dumps(payload, indent=2)}")

                return self.session.post(
                    f"{self.base_url}/validate",
                    json=payload,
                    timeout=10
                )
                
            response = self._make_request_with_retry(make_request)
            
            # First check text-based responses for ban/retry
            response_text = response.text.lower()
            
            # Check for bans
            ban_keys = [
                "limit_exceeded",
                "Invalid or inactive API key",
                "Invalid API key"
            ]
            for key in ban_keys:
                if key.lower() in response_text:
                    return MTResponse(success=False, error=key)

            # Check for retry conditions
            retry_keys = [
                "Server timeout error",
                "Internal server error"
            ]
            for key in retry_keys:
                if key.lower() in response_text:
                    return MTResponse(success=False, error="Server error - please retry")
            
            # Parse JSON response for other cases
            try:
                json_response = response.json()
                
                # For validate endpoint, success is in the root
                if json_response.get("success") is True:
                    return MTResponse(success=True, data=json_response)
                
                # Check for specific error messages
                if json_response.get("error_code") == 401:
                    return MTResponse(success=False, error=json_response.get("message", "Authorization failed"))
                
                # Handle invalid parameters - raise exception to trigger retry
                if json_response.get("message") == "Invalid parameters":
                    raise requests.RequestException("Invalid parameters - retrying with new proxy")
                
                # Handle other error cases
                error_msg = json_response.get("message", "Unknown error")
                if error_msg == "Failed to validate account credentials":
                    raise requests.RequestException("Failed to validate - retrying with new proxy")
                return MTResponse(success=False, error=error_msg)
                
            except json.JSONDecodeError:
                if self._switch_server():
                    # Retry the request with new server
                    return self.validate_account(username, password)
                # Instead of failing, raise an exception to trigger retry with new proxy
                raise requests.RequestException("Invalid response format - retrying with new proxy")
            
        except requests.RequestException as e:
            return MTResponse(success=False, error=f"Request error: {str(e)}")
        except Exception as e:
            return MTResponse(success=False, error=f"Error: {str(e)}")

    def login(self, username: str, password: str, proxy: Optional[Union[str, Dict]] = None) -> MTResponse:
        """
        Login to account and get detailed information.
        
        Args:
            username (str): Account username
            password (str): Account password
            proxy (Union[str, Dict], optional): Proxy configuration
            
        Example payloads:
            Format 1 (With credentials):
            {
                "username": "user@example.com",
                "password": "password123",
                "proxy": {
                    "url": "proxy.example.com:8080",
                    "type": "http",
                    "username": "proxyuser",
                    "password": "proxypass"
                }
            }

            Format 2 (Without credentials):
            {
                "username": "user@example.com",
                "password": "password123",
                "proxy": {
                    "url": "proxy.example.com:8080",
                    "type": "http"
                }
            }

            Format 3 (Simple string):
            {
                "username": "user@example.com",
                "password": "password123",
                "proxy": "proxy.example.com:8080"
            }
            
        Returns:
            MTResponse: Response object containing success status and account info
        """
        is_valid, modified_password, error_msg = self._validate_password_format(password)
        if not is_valid:
            return MTResponse(success=False, error=error_msg)
            
        password = modified_password
        
        try:
            def make_request():
                payload = {
                    "username": username,
                    "password": password
                }
                
                # Handle proxy configuration
                if proxy:
                    if isinstance(proxy, str):
                        payload["proxy"] = proxy
                    elif isinstance(proxy, dict):
                        proxy_data = {}
                        if "url" in proxy:
                            proxy_data["url"] = proxy["url"]
                            proxy_data["type"] = proxy.get("type", "http")
                            
                            if proxy.get("username") and proxy.get("password"):
                                proxy_data["username"] = proxy["username"]
                                proxy_data["password"] = proxy["password"]
                                
                            payload["proxy"] = proxy_data
                        else:
                            payload["proxy"] = proxy

                return self.session.post(
                    f"{self.base_url}/login",
                    json=payload,
                    timeout=15  # Increased timeout
                )
                
            response = self._make_request_with_retry(make_request)
            
            # First check text-based responses for ban/retry
            response_text = response.text.lower()
            
            # Check for bans
            ban_keys = [
                "limit_exceeded",
                "Invalid or inactive API key",
                "Invalid API key",
                "Daily request limit exceeded",
                "Daily validation limit exceeded"
            ]
            for key in ban_keys:
                if key.lower() in response_text:
                    try:
                        json_data = response.json()
                        if "api_key_info" in json_data:
                            info = json_data["api_key_info"]
                            return MTResponse(success=False, error=f"Daily Limit Exceeded! Limit: {info.get('daily_limit', 0)}, Used: {info.get('requests_today', 0)}")
                    except:
                        pass
                    return MTResponse(success=False, error=key)

            # Check for retry conditions
            retry_keys = [
                "Server timeout error",
                "Internal server error",
                "proxy error",
                "Server error",
                "Invalid parameters"
            ]
            for key in retry_keys:
                if key.lower() in response_text:
                    raise requests.RequestException("Server error - please retry")
            
            # Parse JSON response for other cases
            try:
                json_response = response.json()
                
                # For login endpoint, success is in status field
                if json_response.get("status") == "success":
                    return MTResponse(success=True, account_info=json_response)
                
                # Check for specific failure messages
                if json_response.get("status") in ["Invalid password", "Account not found"]:
                    return MTResponse(success=False, error=json_response["status"])
                
                # Handle invalid parameters - raise exception to trigger retry
                if json_response.get("status") == "Invalid parameters":
                    raise requests.RequestException("Invalid parameters - retrying with new proxy")
                
                # Handle empty or invalid response
                if not json_response or "status" not in json_response:
                    raise requests.RequestException("Invalid response format")
                
                # Handle server error status
                if json_response.get("status") == "Server error":
                    raise requests.RequestException("Server error - please retry")
                
                return MTResponse(success=False, error=json_response.get("status", "Unknown error"))
                
            except json.JSONDecodeError:
                if self._switch_server():
                    # Retry the request with new server
                    return self.login(username, password, proxy)
                # Instead of failing, raise an exception to trigger retry with new proxy
                raise requests.RequestException("Invalid response format - retrying with new proxy")
            
        except requests.RequestException as e:
            # Re-raise the exception to trigger retry in check_account
            raise
        except Exception as e:
            return MTResponse(success=False, error=f"Error: {str(e)}")
