# SWM Pool Scraper

The Stadtwerke München (aka SWM) report the pool occupancy of all their indoor poole on a website: 

   https://www.swm.de/baeder/auslastung

In order to feed a machine learning algorithm, I want to scrape them on a regular basis.

## Architecture

A simple Python script, that when called

- Scrapes the website 
- Appends the data to a file

We want to have proper Pytghon modules, we want to save test data (probably to ./test_data) so we can test & tune our extraction part.

Tech Stack:

- Python 3.13
- Beautiful Soup