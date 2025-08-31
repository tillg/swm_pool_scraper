# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python web scraping project for collecting pool occupancy data from Stadtwerke München (SWM). The scraper targets https://www.swm.de/baeder/auslastung to gather indoor pool capacity information for machine learning purposes.

## Architecture

- **Simple Python script**: Single-execution scraper that fetches data and appends to a file
- **Modular design**: Proper Python modules structure planned
- **Test data storage**: Save scraped data to `./test_data/` for development and tuning

## Tech Stack

- **Python 3.13** - Base language
- **Selenium** - Browser automation for JavaScript-rendered content
- **Beautiful Soup** - HTML parsing after page load
- **Requests** - HTTP requests (fallback)
- **CSV/JSON** - Data storage formats
- **Logging** - Error tracking and monitoring

## Development Plan

**Key Finding**: The SWM website loads occupancy data dynamically via JavaScript, requiring browser automation rather than simple HTTP requests.

### Planned Project Structure
```
swm_pool_scraper/
├── src/
│   ├── __init__.py
│   ├── scraper.py          # Main scraping logic with Selenium
│   ├── data_storage.py     # Handle file operations and data persistence  
│   └── models.py           # Data classes for pool occupancy data
├── test_data/              # Store scraped test data
├── scraped_data/           # Store production scraped data
├── main.py                 # Entry point script
├── requirements.txt        # Dependencies
└── config.py              # Configuration settings
```

### Implementation Steps
1. Create modular Python package structure
2. Set up dependencies (Selenium, BeautifulSoup, etc.)
3. Implement browser automation to handle dynamic content
4. Extract pool names, occupancy levels, and timestamps
5. Create data storage system for appending to files
6. Add test data collection to `./test_data/`
7. Build main orchestration script
8. Add error handling, logging, and retry logic

## Project Structure

This is a minimal project currently containing only README.md and basic setup files (.gitignore, .venv). No Python modules, configuration files, or dependency management files exist yet. The codebase is in early planning stage.

## Development Notes

- No build, test, or lint commands are currently configured
- No package management (requirements.txt) is set up yet
- Virtual environment (.venv) created with Python 3.13
- No existing Python code to analyze