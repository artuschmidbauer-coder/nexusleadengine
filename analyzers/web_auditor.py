import re
import time
import socket
import ipaddress
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from typing import Optional, List
from models.schema import TechSignal

def is_safe_public_url(url: str) -> bool:
    """Blocks SSRF attacks by ensuring hostname resolves only to public routable IPs."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname or hostname.lower() in ("localhost", "127.0.0.1", "0.0.0.0"):
            return False
        addr_info = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in addr_info:
            ip = ipaddress.ip_address(sockaddr[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
                return False
        return True
    except Exception:
        return False

class WebAuditor:
    """Audits a business website to detect marketing tech stack and conversion bottlenecks."""

    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }

    def audit(self, url: Optional[str]) -> TechSignal:
        if not url:
            return TechSignal(
                has_ssl=False,
                has_meta_pixel=False,
                has_google_tag=False,
                has_whatsapp_widget=False,
                has_contact_form=False,
                is_mobile_friendly=False,
                page_load_seconds=0.0,
                detected_cms=None,
                social_profiles=[]
            )

        target_url = url if url.startswith(("http://", "https://")) else f"https://{url}"
        if not is_safe_public_url(target_url):
            return TechSignal(
                has_ssl=False,
                has_meta_pixel=False,
                has_google_tag=False,
                has_whatsapp_widget=False,
                has_contact_form=False,
                is_mobile_friendly=False,
                page_load_seconds=0.0,
                detected_cms=None,
                social_profiles=[]
            )

        has_ssl = target_url.startswith("https://")
        start_time = time.time()

        try:
            response = requests.get(target_url, headers=self.headers, timeout=self.timeout, allow_redirects=True)
            load_time = round(time.time() - start_time, 2)
            content = response.text
            soup = BeautifulSoup(content, "html.parser")

            has_meta_pixel = bool(
                re.search(r"connect\.facebook\.net|fbevents\.js|fbq\(", content, re.IGNORECASE)
            )
            has_google_tag = bool(
                re.search(r"googletagmanager\.com|google-analytics\.com|gtag\(", content, re.IGNORECASE)
            )
            has_whatsapp = bool(
                re.search(r"wa\.me|api\.whatsapp\.com|whatsapp", content, re.IGNORECASE)
            )
            has_form = bool(soup.find("form"))

            # Detect CMS
            detected_cms = None
            if "wp-content" in content or "wp-includes" in content:
                detected_cms = "WordPress"
            elif "cdn.shopify.com" in content:
                detected_cms = "Shopify"
            elif "wix.com" in content or "wixsite" in content:
                detected_cms = "Wix"
            elif "squarespace" in content:
                detected_cms = "Squarespace"
            elif "webflow" in content:
                detected_cms = "Webflow"

            # Detect social links
            social_links: List[str] = []
            for a in soup.find_all("a", href=True):
                href = a["href"].lower()
                for platform in ["instagram.com", "facebook.com", "linkedin.com", "tiktok.com"]:
                    if platform in href and href not in social_links:
                        social_links.append(href)

            return TechSignal(
                has_ssl=has_ssl,
                has_meta_pixel=has_meta_pixel,
                has_google_tag=has_google_tag,
                has_whatsapp_widget=has_whatsapp,
                has_contact_form=has_form,
                is_mobile_friendly=True,
                page_load_seconds=load_time,
                detected_cms=detected_cms,
                social_profiles=social_links[:5]
            )

        except Exception:
            # Fallback if host unreachable or in isolated environment
            return TechSignal(
                has_ssl=has_ssl,
                has_meta_pixel=False,
                has_google_tag=False,
                has_whatsapp_widget=False,
                has_contact_form=False,
                is_mobile_friendly=True,
                page_load_seconds=0.0,
                detected_cms=None,
                social_profiles=[]
            )
