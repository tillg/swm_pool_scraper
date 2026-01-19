"""
Integration test: Verify all facilities from SWM website are scraped

This test compares the scraper's facility registry against the known
facilities on the SWM website. It should FAIL if any facilities are missing.

Known facilities (as of 2026-01, verified via browser inspection):
- Pools (9): Bad Giesing-Harlaching, Cosimawellenbad, Dante-Winter-Warmfreibad,
             Michaelibad, Müller'sches Volksbad, Nordbad, Olympia-Schwimmhalle,
             Südbad, Westbad
- Saunas (7): Cosimawellenbad, Dantebad, Michaelibad, Müller'sches Volksbad,
              Nordbad, Südbad, Westbad
- Ice Rinks (1): Prinzregentenstadion - Eislaufbahn
"""

import pytest
from src.api_scraper import SWMAPIScraper


# Expected facilities on the SWM website (verified via browser)
EXPECTED_POOLS = {
    'Bad Giesing-Harlaching',
    'Cosimawellenbad',
    'Dante-Winter-Warmfreibad',
    'Michaelibad',
    "Müller'sches Volksbad",
    'Nordbad',
    'Olympia-Schwimmhalle',
    'Südbad',
    'Westbad',
}

EXPECTED_SAUNAS = {
    'Cosimawellenbad',
    'Dantebad',
    'Michaelibad',
    "Müller'sches Volksbad",
    'Nordbad',
    'Südbad',
    'Westbad',
}

EXPECTED_ICE_RINKS = {
    'Prinzregentenstadion - Eislaufbahn',
}


class TestFacilityCoverage:
    """Test that all facilities on the SWM website are scraped"""

    @pytest.mark.integration
    def test_all_pools_are_registered(self):
        """Verify all pools from website are in scraper registry."""
        scraper = SWMAPIScraper()

        # Get pools from registry
        registry_pools = {
            f.name for f in scraper.registry.facilities.values()
            if f.active and f.facility_type.value == 'pool'
        }

        print(f"\n[Expected] {len(EXPECTED_POOLS)} pools on website:")
        for name in sorted(EXPECTED_POOLS):
            print(f"  - {name}")

        print(f"\n[Scraper] {len(registry_pools)} pools in registry:")
        for name in sorted(registry_pools):
            print(f"  - {name}")

        missing = EXPECTED_POOLS - registry_pools
        if missing:
            print(f"\n[ERROR] Missing pools: {missing}")

        assert not missing, f"Scraper is missing pools: {missing}"

    @pytest.mark.integration
    def test_all_saunas_are_registered(self):
        """Verify all saunas from website are in scraper registry."""
        scraper = SWMAPIScraper()

        # Get saunas from registry
        registry_saunas = {
            f.name for f in scraper.registry.facilities.values()
            if f.active and f.facility_type.value == 'sauna'
        }

        print(f"\n[Expected] {len(EXPECTED_SAUNAS)} saunas on website:")
        for name in sorted(EXPECTED_SAUNAS):
            print(f"  - {name}")

        print(f"\n[Scraper] {len(registry_saunas)} saunas in registry:")
        for name in sorted(registry_saunas):
            print(f"  - {name}")

        missing = EXPECTED_SAUNAS - registry_saunas
        if missing:
            print(f"\n[ERROR] Missing saunas: {missing}")

        assert not missing, f"Scraper is missing saunas: {missing}"

    @pytest.mark.integration
    def test_all_ice_rinks_are_registered(self):
        """Verify all ice rinks from website are in scraper registry."""
        scraper = SWMAPIScraper()

        # Get ice rinks from registry
        registry_ice_rinks = {
            f.name for f in scraper.registry.facilities.values()
            if f.active and f.facility_type.value == 'ice_rink'
        }

        print(f"\n[Expected] {len(EXPECTED_ICE_RINKS)} ice rinks on website:")
        for name in sorted(EXPECTED_ICE_RINKS):
            print(f"  - {name}")

        print(f"\n[Scraper] {len(registry_ice_rinks)} ice rinks in registry:")
        for name in sorted(registry_ice_rinks):
            print(f"  - {name}")

        missing = EXPECTED_ICE_RINKS - registry_ice_rinks
        if missing:
            print(f"\n[ERROR] Missing ice rinks: {missing}")

        assert not missing, f"Scraper is missing ice rinks: {missing}"

    @pytest.mark.integration
    def test_total_facility_count(self):
        """Verify total facility count matches website."""
        scraper = SWMAPIScraper()

        expected_total = len(EXPECTED_POOLS) + len(EXPECTED_SAUNAS) + len(EXPECTED_ICE_RINKS)
        registry_total = len([f for f in scraper.registry.facilities.values() if f.active])

        print(f"\n[Expected] {expected_total} total facilities on website")
        print(f"  - {len(EXPECTED_POOLS)} pools")
        print(f"  - {len(EXPECTED_SAUNAS)} saunas")
        print(f"  - {len(EXPECTED_ICE_RINKS)} ice rinks")

        print(f"\n[Scraper] {registry_total} total facilities in registry")

        # List all registered facilities by type
        for facility_type in ['pool', 'sauna', 'ice_rink']:
            facilities = [f for f in scraper.registry.facilities.values()
                         if f.active and f.facility_type.value == facility_type]
            print(f"  - {len(facilities)} {facility_type}s")

        assert registry_total >= expected_total, (
            f"Scraper is missing facilities! "
            f"Website has {expected_total}, registry has {registry_total}. "
            f"Missing {expected_total - registry_total} facilities."
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s', '--tb=short'])
