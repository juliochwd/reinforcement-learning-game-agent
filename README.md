# Game Agent - Data Scraper Edition

## Overview

This project provides a specialized tool for scraping game data from the "Win Go" platform. Originally designed as a full-fledged reinforcement learning agent, the application has been refactored to focus exclusively on data collection. It features a user-friendly graphical user interface (GUI) that allows users to initiate and monitor the scraping process in real-time.

The application is built with Python and utilizes the Selenium library for web automation, enabling it to navigate the game's website, log in, and systematically collect historical data. All operations are managed through a clean and intuitive interface, making it accessible even for users with limited technical expertise.

## Features

- **Modern GUI**: Built with CustomTkinter for a modern, dark-themed interface
- **Automated Web Scraping**: Uses Selenium with Selenium Wire for advanced web automation
- **Real-Time Progress Monitoring**: Live progress bars, ETA estimates, and detailed logging
- **Configuration-Driven**: All settings managed through `config.yaml`
- **Robust Error Handling**: Built-in error recovery and retry mechanisms
- **Data Processing**: Advanced data handling with pandas and numpy
- **Secure Credential Management**: No hardcoded credentials

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Chrome browser (recommended)
- ChromeDriver (auto-managed by webdriver-manager)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/reinforcement-learning-game-agent.git
   cd reinforcement-learning-game-agent
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. **Install the required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

Before running the application, configure `config.yaml`:

1. **Web Agent Settings**:
   - `login_url`: Game login page URL
   - `api_endpoint`: Data collection API endpoint
   - `initial_balance`: Initial game account balance

2. **Scraping Parameters**:
   - `max_pages`: Maximum pages to scrape
   - `zoom_level`: Browser zoom level
   - `timeouts`: Various timeout settings

3. **UI Configuration**:
   - Window size and appearance
   - Progress indicators
   - Logging settings

### Running the Application

```bash
python main.py
```

This launches the modern GUI where you can:
- Start data scraping with "Start Scraping" button
- Monitor real-time progress
- View detailed logs
- Manage scraping parameters

## Project Structure
