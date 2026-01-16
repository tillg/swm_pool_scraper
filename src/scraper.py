import logging
import time
from datetime import datetime
from typing import List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

from .models import PoolOccupancy
from config import SWM_URL, SELENIUM_CONFIG, TIMEZONE


class SWMPoolScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver: Optional[webdriver.Chrome] = None
        self.logger = logging.getLogger(__name__)
        
    def _setup_driver(self) -> webdriver.Chrome:
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.implicitly_wait(SELENIUM_CONFIG["implicit_wait"])
        driver.set_page_load_timeout(SELENIUM_CONFIG["page_load_timeout"])
        
        return driver
    
    def __enter__(self):
        self.driver = self._setup_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()
    
    def scrape_pool_data(self) -> List[PoolOccupancy]:
        if not self.driver:
            raise RuntimeError("Driver not initialized. Use as context manager.")
        
        try:
            self.logger.info(f"Loading SWM pool occupancy page: {SWM_URL}")
            self.driver.get(SWM_URL)
            
            self.logger.info("Waiting for page to load completely...")
            time.sleep(5)
            
            wait = WebDriverWait(self.driver, 20)
            try:
                wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
                self.logger.info("Page loaded successfully")
            except TimeoutException:
                self.logger.warning("Page may not be fully loaded, continuing anyway...")
            
            time.sleep(5)
            
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            self.logger.info("Parsing pool data from loaded page...")
            return self._parse_pool_data(soup)
            
        except TimeoutException:
            self.logger.error("Timeout waiting for pool data to load")
            page_source = self.driver.page_source if self.driver else ""
            if page_source:
                soup = BeautifulSoup(page_source, 'html.parser')
                self._save_debug_html(soup)
            raise
        except WebDriverException as e:
            self.logger.error(f"WebDriver error: {e}")
            raise
    
    def _parse_pool_data(self, soup: BeautifulSoup) -> List[PoolOccupancy]:
        pools = []
        timestamp = datetime.now(TIMEZONE)
        
        self.logger.info("Parsing pool data using regex pattern matching...")
        pools = self._regex_parse(soup, timestamp)
        
        if not pools:
            self.logger.warning("No pool data found. HTML structure may have changed.")
            self._save_debug_html(soup)
        
        self.logger.info(f"Scraped data for {len(pools)} pools")
        return pools
    
    
    def _save_debug_html(self, soup: BeautifulSoup):
        from config import TEST_DATA_DIR
        debug_file = TEST_DATA_DIR / f"debug_html_{datetime.now(TIMEZONE).strftime('%Y%m%d_%H%M%S')}.html"
        debug_file.parent.mkdir(exist_ok=True)
        
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        
        self.logger.info(f"Debug HTML saved to: {debug_file}")
    
    def _regex_parse(self, soup: BeautifulSoup, timestamp: datetime) -> List[PoolOccupancy]:
        """Regex-based parsing method that extracts pool occupancy data from page text"""
        pools = []
        
        all_text = soup.get_text()
        
        import re
        
        # Split text to find pools vs saunas sections
        pool_section_match = re.search(r'Echtzeit-Auslastung der Hallenbäder(.*?)Echtzeit-Auslastung der Saunen', all_text, re.DOTALL)
        sauna_section_match = re.search(r'Echtzeit-Auslastung der Saunen(.*?)(?:Auszeichnungen|$)', all_text, re.DOTALL)
        
        pool_text = pool_section_match.group(1) if pool_section_match else ""
        sauna_text = sauna_section_match.group(1) if sauna_section_match else ""
        
        self.logger.info(f"Found pool section: {len(pool_text)} chars, sauna section: {len(sauna_text)} chars")
        
        # Parse pools
        pools.extend(self._parse_facilities(pool_text, "pool", timestamp))
        
        # Parse saunas  
        pools.extend(self._parse_facilities(sauna_text, "sauna", timestamp))
        
        # Fallback: parse entire text if sections not found
        if not pools:
            self.logger.info("Section-based parsing failed, trying fallback...")
            pools.extend(self._parse_facilities(all_text, "unknown", timestamp))
        
        return pools
    
    def _parse_facilities(self, text: str, facility_type: str, timestamp: datetime) -> List[PoolOccupancy]:
        """Parse facilities from a text section"""
        facilities = []
        
        import re
        
        specific_patterns = [
            r'(Bad Giesing-Harlaching)\s*(?:Mehr Infos)?\s*(\d+\s*%\s*frei)',
            r'(Cosimawellenbad)\s*(?:Mehr Infos)?\s*(\d+\s*%\s*frei)',
            r'(Michaelibad)\s*(?:Mehr Infos)?\s*(\d+\s*%\s*frei)',
            r'(Müller\'sches Volksbad)\s*(?:Mehr Infos)?\s*(\d+\s*%\s*frei)',
            r'(Nordbad)\s*(?:Mehr Infos)?\s*(\d+\s*%\s*frei)',
            r'(Südbad)\s*(?:Mehr Infos)?\s*(\d+\s*%\s*frei)',
            r'(Westbad)\s*(?:Mehr Infos)?\s*(\d+\s*%\s*frei)',
            r'(Dantebad)\s*(?:Mehr Infos)?\s*(\d+\s*%\s*frei)',
        ]
        
        for pattern in specific_patterns:
            matches = re.findall(pattern, text)
            for facility_name, occupancy in matches:
                facility_name = facility_name.strip()
                occupancy = occupancy.strip()
                
                if facility_name and occupancy:
                    pool_occupancy = PoolOccupancy(
                        pool_name=facility_name,
                        occupancy_level=occupancy,
                        timestamp=timestamp,
                        raw_occupancy=f"{facility_name}: {occupancy}"
                    )
                    pool_occupancy.facility_type = facility_type
                    facilities.append(pool_occupancy)
                    self.logger.info(f"Parsed {facility_type}: {facility_name} - {occupancy}")
        
        return facilities