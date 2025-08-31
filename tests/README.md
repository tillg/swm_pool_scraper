# Test Suite Documentation

## Overview

Comprehensive unit tests for the SWM Pool Scraper project, providing safety net for future changes and validating current functionality.

## Test Coverage

### 🏗️ **test_models.py** (10 tests)
- **PoolOccupancy data model validation**
- Property calculations (occupancy_percent, time features)
- Data export formats (CSV, JSON)
- Edge cases and Unicode handling

### 🌐 **test_api_scraper.py** (16 tests)  
- **HTTP API calls with mocking**
- Rate limiting and error handling
- Facility registry integration
- Monitoring system functionality
- Context manager patterns
- End-to-end integration tests

### 💾 **test_data_storage.py** (17 tests)
- **File operations (CSV/JSON)**
- Directory handling and permissions
- Data format validation
- Append vs create modes
- Unicode and edge case handling

## Running Tests

### Quick Start
```bash
# Run all tests
source .venv/bin/activate && python -m pytest tests/ -v

# Use the test runner script
python run_tests.py all
```

### Specific Test Suites
```bash
# Individual test files
python run_tests.py models
python run_tests.py api  
python run_tests.py storage

# Quick tests (no selenium dependencies)
python run_tests.py quick
```

### Test Options
```bash
# Verbose output with details
pytest tests/ -v

# Run specific test
pytest tests/test_models.py::TestPoolOccupancy::test_occupancy_percent_extraction -v

# Show coverage (requires pytest-cov)
pytest tests/ --cov=src --cov-report=html
```

## Test Architecture

### Mocking Strategy
- **HTTP requests**: Mocked to prevent external API calls
- **File system**: Uses temporary directories for isolation
- **Selenium**: Completely mocked to avoid browser dependencies
- **Time/datetime**: Fixed timestamps for predictable results

### Fixtures
- **temp_dir**: Temporary directories for file operations
- **sample_pool_data**: Realistic test data for validation
- **mock_registry**: Pre-configured facility registry

### Best Practices
- **Isolation**: Each test runs independently
- **Deterministic**: Fixed dates/times for consistent results
- **Fast**: All tests run in ~1.5 seconds
- **Comprehensive**: Covers success cases, failures, and edge cases

## Key Test Features

### ✅ **What's Validated**
- API response parsing and error handling
- Data model property calculations
- File I/O operations and formats  
- Unicode and special character handling
- Weekend/weekday detection logic
- CSV/JSON data export formats
- Facility type categorization
- Rate limiting and retry mechanisms

### 🔄 **Mock Coverage**
- External HTTP calls to Ticos API
- Selenium browser automation
- File system operations
- Configuration loading
- Time-dependent operations

### 🏆 **Quality Metrics**
- **43 test cases** covering core functionality
- **100% pass rate** with comprehensive assertions  
- **No external dependencies** required for testing
- **Fast execution** suitable for CI/CD pipelines

## Adding New Tests

### Test File Structure
```python
class TestNewFeature:
    
    @pytest.fixture
    def setup_data(self):
        """Setup test data"""
        return test_data
    
    def test_success_case(self, setup_data):
        """Test normal operation"""
        result = function_under_test(setup_data)
        assert result == expected_value
    
    def test_error_handling(self):
        """Test error conditions"""
        with pytest.raises(ExpectedError):
            function_under_test(invalid_input)
```

### Naming Conventions
- **Test files**: `test_module_name.py`
- **Test classes**: `TestClassName`
- **Test methods**: `test_specific_behavior`
- **Fixtures**: `descriptive_setup_name`

### When to Add Tests
- ✅ New functionality or features
- ✅ Bug fixes (add regression test)
- ✅ Refactoring existing code
- ✅ Configuration changes
- ✅ Data format modifications

## Integration with Development

### Pre-commit Testing
```bash
# Run before committing changes
python run_tests.py all
```

### CI/CD Integration
```yaml
# Example GitHub Actions step
- name: Run Tests
  run: |
    source .venv/bin/activate
    pip install pytest pytest-mock
    pytest tests/ -v
```

### Debugging Failed Tests
```bash
# Run with maximum verbosity
pytest tests/failing_test.py -vv -s

# Run single test with debugging
pytest tests/test_file.py::test_method -v --pdb
```

This test suite ensures the SWM Pool Scraper remains reliable and maintainable as it evolves.