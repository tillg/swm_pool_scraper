"""
Unit tests for API scraper functionality
Tests HTTP calls, data parsing, and facility management with mocking
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.api_scraper import SWMAPIScraper, ManagedAPIScraper
from src.facility_registry import FacilityRegistry, Facility
from src.facilities import FacilityType


class TestSWMAPIScraper:

    @pytest.fixture
    def scraper(self):
        """Create scraper with real registry (from facilities.py)"""
        return SWMAPIScraper()

    def test_initialization(self):
        """Test scraper initialization"""
        scraper = SWMAPIScraper()

        assert scraper.API_BASE == "https://counter.ticos-systems.cloud/api/gates/counter"
        assert scraper.session is not None
        assert scraper.registry is not None
        assert len(scraper.registry.facilities) == 17  # All facilities from facilities.py

    def test_fetch_occupancy_success(self, scraper):
        """Test successful API call"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{
            "organizationUnitId": 30195,
            "personCount": 72,
            "maxPersonCount": 311
        }]
        mock_response.raise_for_status.return_value = None

        with patch.object(scraper.session, 'get', return_value=mock_response):
            result = scraper.fetch_occupancy(30195)

            assert result is not None
            assert result["organizationUnitId"] == 30195
            assert result["personCount"] == 72
            assert result["maxPersonCount"] == 311

    def test_fetch_occupancy_http_error(self, scraper):
        """Test API call with HTTP error"""
        import requests

        with patch.object(
            scraper.session, 'get',
            side_effect=requests.exceptions.RequestException("HTTP 500")
        ):
            result = scraper.fetch_occupancy(30195)
            assert result is None

    def test_fetch_occupancy_empty_response(self, scraper):
        """Test API call with empty response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None

        with patch.object(scraper.session, 'get', return_value=mock_response):
            result = scraper.fetch_occupancy(30195)
            assert result is None

    def test_fetch_occupancy_timeout(self, scraper):
        """Test API call timeout"""
        import requests

        with patch.object(
            scraper.session, 'get',
            side_effect=requests.exceptions.Timeout
        ):
            result = scraper.fetch_occupancy(30195)
            assert result is None

    @patch('src.api_scraper.time.sleep')
    def test_scrape_pool_data_success(self, mock_sleep, scraper):
        """Test successful pool data scraping"""
        # Mock API response for all facilities
        def mock_fetch_occupancy(org_id):
            return {
                "organizationUnitId": org_id,
                "personCount": 50,
                "maxPersonCount": 200
            }

        with patch.object(scraper, 'fetch_occupancy', side_effect=mock_fetch_occupancy):
            pool_data = scraper.scrape_pool_data()

            # Should get data for all 17 facilities
            assert len(pool_data) == 17

            # Check data structure
            pool = next(p for p in pool_data if p.pool_name == "Bad Giesing-Harlaching")
            assert pool.facility_type == "pool"
            assert "frei" in pool.occupancy_level
            assert pool.timestamp is not None

            # Check occupancy calculation (50/200 = 25% occupied, so 75% free)
            expected_percent = round((1 - 50/200) * 100)
            assert pool.occupancy_percent == expected_percent

    @patch('src.api_scraper.time.sleep')
    def test_scrape_pool_data_with_failures(self, mock_sleep, scraper):
        """Test scraping with some API failures"""
        # Only return data for one facility
        def mock_fetch_occupancy(org_id):
            if org_id == 30195:
                return {
                    "organizationUnitId": 30195,
                    "personCount": 50,
                    "maxPersonCount": 311
                }
            return None

        with patch.object(scraper, 'fetch_occupancy', side_effect=mock_fetch_occupancy):
            pool_data = scraper.scrape_pool_data()

            # Should only get data for successful API call
            assert len(pool_data) == 1
            assert pool_data[0].pool_name == "Bad Giesing-Harlaching"

    @patch('src.api_scraper.time.sleep')
    def test_rate_limiting_sleep(self, mock_sleep, scraper):
        """Test that rate limiting sleep is called"""
        with patch.object(scraper, 'fetch_occupancy', return_value=None):
            scraper.scrape_pool_data()

            # Should call sleep for each facility (rate limiting)
            assert mock_sleep.call_count == 17  # 17 facilities
            mock_sleep.assert_called_with(0.1)

    def test_all_facility_types_present(self, scraper):
        """Test that all facility types are represented"""
        pools = scraper.registry.get_facilities_by_type(FacilityType.POOL)
        saunas = scraper.registry.get_facilities_by_type(FacilityType.SAUNA)
        ice_rinks = scraper.registry.get_facilities_by_type(FacilityType.ICE_RINK)

        assert len(pools) == 9
        assert len(saunas) == 7
        assert len(ice_rinks) == 1


class TestManagedAPIScraper:

    def test_context_manager(self):
        """Test context manager functionality"""
        with ManagedAPIScraper() as scraper:
            assert isinstance(scraper, SWMAPIScraper)
            assert scraper.session is not None

    def test_context_manager_with_exception(self):
        """Test context manager cleanup on exception"""
        try:
            with ManagedAPIScraper() as scraper:
                assert isinstance(scraper, SWMAPIScraper)
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected exception


class TestIntegration:
    """Integration tests that test multiple components together"""

    @patch('src.api_scraper.time.sleep')
    def test_end_to_end_scraping(self, mock_sleep):
        """Test complete scraping workflow"""
        # Mock API responses
        mock_api_responses = {
            30195: {"organizationUnitId": 30195, "personCount": 50, "maxPersonCount": 311},
            30190: {"organizationUnitId": 30190, "personCount": 100, "maxPersonCount": 530},
        }

        def mock_response(url, **kwargs):
            org_id = int(url.split('organizationUnitIds=')[1])

            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.raise_for_status.return_value = None

            if org_id in mock_api_responses:
                mock_resp.json.return_value = [mock_api_responses[org_id]]
            else:
                mock_resp.json.return_value = []

            return mock_resp

        with patch('requests.Session.get', side_effect=mock_response):
            scraper = SWMAPIScraper()
            pool_data = scraper.scrape_pool_data()

            # Should only get data for facilities with API responses
            assert len(pool_data) == 2

            # Verify pool data
            pool_names = [p.pool_name for p in pool_data]
            assert "Bad Giesing-Harlaching" in pool_names
            assert "Cosimawellenbad" in pool_names

            # Verify occupancy calculations
            pool_data_by_name = {p.pool_name: p for p in pool_data}
            pool_occupancy = pool_data_by_name["Bad Giesing-Harlaching"].occupancy_percent
            expected_pool = round((1 - 50/311) * 100)  # 84% free
            assert pool_occupancy == expected_pool
