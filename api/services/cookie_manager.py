"""
Cookie Manager for MediaCrawler platforms
Manages login cookies for different platforms
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any
import logging

from api.config import settings

logger = logging.getLogger(__name__)


class CookieManager:
    """
    Manages cookies for different platforms
    """

    def __init__(self):
        # 根据环境选择存储路径
        if settings.is_production and os.path.exists("/data"):
            # 生产环境使用持久化Volume
            self.cookie_dir = Path("/data/cookies")
        else:
            # 开发环境使用本地目录
            self.cookie_dir = Path("data/cookies")

        self.cookie_dir.mkdir(parents=True, exist_ok=True)

        # Cookie文件路径
        self.cookie_file = self.cookie_dir / "platform_cookies.json"
        logger.info(f"Cookie storage path: {self.cookie_file}")

        # 平台配置
        self.platforms = {
            "xiaohongshu": {
                "name": "小红书",
                "url": "https://www.xiaohongshu.com",
                "key_fields": ["web_session", "a1"],
                "expire_days": 7
            },
            "weibo": {
                "name": "微博",
                "url": "https://weibo.com",
                "key_fields": ["SUB", "SUBP"],
                "expire_days": 30
            },
            "douyin": {
                "name": "抖音",
                "url": "https://www.douyin.com",
                "key_fields": ["sessionid", "sid_tt"],
                "expire_days": 7
            }
        }

        # 加载已保存的cookies
        self.cookies = self._load_cookies()

    def _load_cookies(self) -> Dict[str, Dict[str, Any]]:
        """
        Load cookies from file
        """
        if self.cookie_file.exists():
            try:
                with open(self.cookie_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load cookies: {e}")
        return {}

    def _save_cookies(self):
        """
        Save cookies to file
        """
        try:
            with open(self.cookie_file, "w", encoding="utf-8") as f:
                json.dump(self.cookies, f, indent=2, ensure_ascii=False)
            logger.info("Cookies saved successfully")
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")

    def set_cookie(self, platform: str, cookie_string: str, login_type: str = "cookie") -> bool:
        """
        Set cookie for a platform

        Args:
            platform: Platform name (xiaohongshu, weibo, douyin)
            cookie_string: Cookie string
            login_type: Login type (cookie, qrcode, phone)

        Returns:
            True if successful
        """
        if platform not in self.platforms:
            logger.error(f"Unknown platform: {platform}")
            return False

        # Parse cookie string if needed
        if isinstance(cookie_string, str) and "=" in cookie_string:
            cookie_dict = {}
            for item in cookie_string.split(";"):
                item = item.strip()
                if "=" in item:
                    key, value = item.split("=", 1)
                    cookie_dict[key.strip()] = value.strip()
        else:
            cookie_dict = cookie_string if isinstance(cookie_string, dict) else {}

        # Check required fields
        platform_config = self.platforms[platform]
        missing_fields = []
        for field in platform_config.get("key_fields", []):
            if field not in cookie_dict:
                missing_fields.append(field)

        if missing_fields and login_type == "cookie":
            logger.warning(f"Missing required cookie fields for {platform}: {missing_fields}")

        # Save cookie
        self.cookies[platform] = {
            "cookie_string": cookie_string,
            "cookie_dict": cookie_dict,
            "login_type": login_type,
            "updated_at": datetime.now().isoformat(),
            "expire_at": (datetime.now() + timedelta(days=platform_config.get("expire_days", 7))).isoformat()
        }

        self._save_cookies()
        logger.info(f"Cookie set for {platform}")
        return True

    def get_cookie(self, platform: str) -> Optional[Dict[str, Any]]:
        """
        Get cookie for a platform

        Args:
            platform: Platform name

        Returns:
            Cookie data or None
        """
        cookie_data = self.cookies.get(platform)
        if not cookie_data:
            # Try to load from environment variable
            env_key = f"{platform.upper()}_COOKIES"
            env_cookie = os.getenv(env_key)
            if env_cookie:
                self.set_cookie(platform, env_cookie)
                return self.cookies.get(platform)
            return None

        # Check if expired
        expire_at = cookie_data.get("expire_at")
        if expire_at:
            expire_time = datetime.fromisoformat(expire_at)
            if datetime.now() > expire_time:
                logger.warning(f"Cookie for {platform} has expired")
                # Don't return expired cookie, but keep it for reference

        return cookie_data

    def get_cookie_string(self, platform: str) -> Optional[str]:
        """
        Get cookie string for a platform
        """
        cookie_data = self.get_cookie(platform)
        if cookie_data:
            return cookie_data.get("cookie_string", "")
        return None

    def get_login_config(self, platform: str) -> Dict[str, Any]:
        """
        Get login configuration for a platform

        Returns:
            Login configuration dict
        """
        cookie_data = self.get_cookie(platform)

        if cookie_data:
            return {
                "login_type": cookie_data.get("login_type", "cookie"),
                "cookies": cookie_data.get("cookie_string", ""),
                "save_login_state": True
            }

        # Default to qrcode login if no cookie
        return {
            "login_type": "qrcode",
            "cookies": "",
            "save_login_state": True,
            "headless": False  # Need to show browser for QR code
        }

    def is_cookie_valid(self, platform: str) -> bool:
        """
        Check if cookie is valid (not expired)
        """
        cookie_data = self.get_cookie(platform)
        if not cookie_data:
            return False

        expire_at = cookie_data.get("expire_at")
        if expire_at:
            expire_time = datetime.fromisoformat(expire_at)
            return datetime.now() < expire_time

        return True

    def list_cookies(self) -> Dict[str, Dict[str, Any]]:
        """
        List all cookies with status
        """
        result = {}
        for platform, config in self.platforms.items():
            cookie_data = self.cookies.get(platform)
            if cookie_data:
                is_valid = self.is_cookie_valid(platform)
                result[platform] = {
                    "name": config["name"],
                    "has_cookie": True,
                    "login_type": cookie_data.get("login_type", "unknown"),
                    "is_valid": is_valid,
                    "updated_at": cookie_data.get("updated_at"),
                    "expire_at": cookie_data.get("expire_at")
                }
            else:
                result[platform] = {
                    "name": config["name"],
                    "has_cookie": False,
                    "is_valid": False
                }
        return result

    def clear_cookie(self, platform: str) -> bool:
        """
        Clear cookie for a platform
        """
        if platform in self.cookies:
            del self.cookies[platform]
            self._save_cookies()
            logger.info(f"Cookie cleared for {platform}")
            return True
        return False

    def clear_all_cookies(self) -> bool:
        """
        Clear all cookies
        """
        self.cookies = {}
        self._save_cookies()
        logger.info("All cookies cleared")
        return True

    def update_from_env(self):
        """
        Update cookies from environment variables
        """
        for platform in self.platforms:
            env_key = f"{platform.upper()}_COOKIES"
            env_cookie = os.getenv(env_key)
            if env_cookie:
                self.set_cookie(platform, env_cookie)
                logger.info(f"Updated {platform} cookie from environment")

    def get_platform_url(self, platform: str) -> Optional[str]:
        """
        Get platform URL for manual login
        """
        config = self.platforms.get(platform)
        if config:
            return config.get("url")
        return None


# Singleton instance
_cookie_manager: Optional[CookieManager] = None


def get_cookie_manager() -> CookieManager:
    """
    Get singleton instance of CookieManager
    """
    global _cookie_manager
    if _cookie_manager is None:
        _cookie_manager = CookieManager()
        # Auto-load from environment on first use
        _cookie_manager.update_from_env()
    return _cookie_manager