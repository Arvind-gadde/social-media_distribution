"""Web scraping service with anti-detection features.

Provides both Playwright (for JavaScript-heavy sites) and httpx (for static sites)
scraping capabilities with anti-detection measures.
"""
import asyncio
import random
from typing import Optional
import structlog
import httpx
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout

log = structlog.get_logger(__name__)


class WebScraper:
    """Web scraper with anti-detection capabilities."""
    
    # User agents for rotation
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    ]
    
    def __init__(self):
        self._browser: Optional[Browser] = None
        self._playwright = None
    
    async def __aenter__(self):
        """Context manager entry."""
        await self._init_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()
    
    async def _init_browser(self):
        """Initialize Playwright browser."""
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )
            log.info("scraper.browser_initialized")
    
    async def close(self):
        """Close browser and cleanup."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
            log.info("scraper.browser_closed")
    
    def _get_random_user_agent(self) -> str:
        """Get random user agent for anti-detection."""
        return random.choice(self.USER_AGENTS)
    
    async def _add_human_behavior(self, page: Page):
        """Add human-like behavior to avoid detection."""
        # Random delay
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # Random mouse movement
        await page.mouse.move(
            random.randint(100, 500),
            random.randint(100, 500)
        )
        
        # Random scroll
        await page.evaluate(f"window.scrollBy(0, {random.randint(100, 300)})")
        await asyncio.sleep(random.uniform(0.3, 0.8))
    
    async def scrape_with_playwright(
        self,
        url: str,
        wait_for_selector: Optional[str] = None,
        timeout: int = 30000,
    ) -> str:
        """Scrape JavaScript-heavy sites with Playwright.
        
        Args:
            url: URL to scrape
            wait_for_selector: CSS selector to wait for before returning
            timeout: Timeout in milliseconds
            
        Returns:
            HTML content of the page
            
        Raises:
            Exception: If scraping fails
        """
        await self._init_browser()
        
        context = await self._browser.new_context(
            user_agent=self._get_random_user_agent(),
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
        )
        
        page = await context.new_page()
        
        try:
            log.info("scraper.playwright.started", url=url)
            
            # Navigate to page
            await page.goto(url, wait_until='domcontentloaded', timeout=timeout)
            
            # Add human behavior
            await self._add_human_behavior(page)
            
            # Wait for specific selector if provided
            if wait_for_selector:
                try:
                    await page.wait_for_selector(wait_for_selector, timeout=timeout)
                except PlaywrightTimeout:
                    log.warning("scraper.playwright.selector_timeout",
                               url=url,
                               selector=wait_for_selector)
            
            # Get page content
            content = await page.content()
            
            log.info("scraper.playwright.success",
                    url=url,
                    content_length=len(content))
            
            return content
        
        except Exception as e:
            log.error("scraper.playwright.failed",
                     url=url,
                     error=str(e),
                     error_type=type(e).__name__)
            raise
        
        finally:
            await page.close()
            await context.close()
    
    async def scrape_with_httpx(
        self,
        url: str,
        headers: Optional[dict] = None,
        timeout: int = 30,
    ) -> str:
        """Scrape static sites with httpx.
        
        Args:
            url: URL to scrape
            headers: Optional custom headers
            timeout: Timeout in seconds
            
        Returns:
            HTML content of the page
            
        Raises:
            Exception: If scraping fails
        """
        default_headers = {
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        if headers:
            default_headers.update(headers)
        
        try:
            log.info("scraper.httpx.started", url=url)
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, headers=default_headers, follow_redirects=True)
                response.raise_for_status()
                
                content = response.text
                
                log.info("scraper.httpx.success",
                        url=url,
                        status_code=response.status_code,
                        content_length=len(content))
                
                return content
        
        except httpx.HTTPStatusError as e:
            log.error("scraper.httpx.http_error",
                     url=url,
                     status_code=e.response.status_code,
                     error=str(e))
            raise
        
        except Exception as e:
            log.error("scraper.httpx.failed",
                     url=url,
                     error=str(e),
                     error_type=type(e).__name__)
            raise
