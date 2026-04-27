import json
import time
from pathlib import Path
from typing import Optional, Dict


class GrowwTokenCache:
    """Cache Groww access tokens to avoid rate-limited re-authentication"""

    def __init__(self, cache_dir: str = "/tmp/madstreaks"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "groww_token.json"
        self.token_lifespan = 3600  # Groww tokens valid for 1 hour
        self.safety_buffer = 300  # Refresh 5 min before actual expiry

    def get_cached_token(self) -> Optional[str]:
        """Retrieve cached token if still valid"""
        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file, 'r') as f:
                data = json.load(f)

            token = data.get("access_token")
            issued_at = data.get("issued_at", 0)
            current_time = time.time()
            age = current_time - issued_at

            # Token valid if age < lifespan - safety_buffer
            if age < (self.token_lifespan - self.safety_buffer):
                return token
            else:
                return None
        except Exception as e:
            return None

    def save_token(self, access_token: str) -> None:
        """Save token with timestamp"""
        try:
            data = {
                "access_token": access_token,
                "issued_at": time.time(),
                "expires_at": time.time() + self.token_lifespan
            }
            with open(self.cache_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            pass  # Fail silently, will just re-auth next time

    def clear_cache(self) -> None:
        """Clear cached token (on error, force re-auth)"""
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
        except Exception:
            pass
