# Game Agent - Data Scraper Edition

## Overview

This project provides a specialized tool for scraping game data from the "Win Go" platform. Originally designed as a full-fledged reinforcement learning agent, the application has been refactored to focus exclusively on data collection. It features a user-friendly graphical user interface (GUI) that allows users to initiate and monitor the scraping process in real-time.

The application is built with Python and utilizes the Selenium library for web automation, enabling it to navigate the game's website, log in, and systematically collect historical data. All operations are managed through a clean and intuitive interface, making it accessible even for users with limited technical expertise.

## Features

- **GUI-Based Operation**: A simple and intuitive graphical interface built with Tkinter allows for easy control over the data scraping process.
- **Automated Web Scraping**: The agent uses Selenium to automate browser interactions, including login and navigation to the game's data sections.
- **Real-Time Progress Monitoring**: The GUI provides real-time feedback on the scraping process, including progress bars, ETA estimates, and detailed logging.
- **Configuration-Driven**: All settings, including URLs, credentials, and scraping parameters, are managed through a central `config.yaml` file, making it easy to customize the agent's behavior.
- **Robust and Reliable**: The agent is designed to handle common web scraping challenges, with built-in error handling and recovery mechanisms.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- A modern web browser (Chrome is recommended)
- ChromeDriver, with its version matching your installed Chrome version

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

Before running the application, you need to configure it by editing the `config.yaml` file:

1. **Web Agent Settings**:
   - `login_url`: The URL of the game's login page.
   - `api_endpoint`: The API endpoint for data collection.
   - `initial_balance`: The initial balance for the game account.

2. **Credentials**:
   - The application will prompt for your phone number and password when you start the scraping process. These are not stored in the configuration file for security reasons.

3. **Scraping Parameters**:
   - `max_pages`: The maximum number of pages to scrape.
   - `zoom_level`: The browser zoom level to use during scraping.

### Running the Application

To start the application, run the `main.py` script from the project's root directory:

```bash
python main.py
```

This will launch the GUI, where you can start the data scraping process by clicking the "Start Scraping" button. The application will then prompt you for your login credentials and begin the scraping process, with all progress and logs displayed in the main window.

## Project Structure

- **`main.py`**: The entry point for the application.
- **`config.yaml`**: The central configuration file for all settings.
- **`src/`**: The main source code directory.
  - **`app/`**: Contains the GUI and task orchestration logic.
    - **`gui.py`**: Defines the main application window and its components.
    - **`task_orchestrator.py`**: Manages background tasks to keep the GUI responsive.
  - **`rl_agent/`**: Contains the core logic for the web scraping agent.
    - **`realtime_agent.py`**: The main class for the scraping agent.
    - **`browser_manager.py`**: Handles browser initialization, login, and navigation.
    - **`data_scraper.py`**: Implements the data scraping logic.
- **`data/`**: The default directory for storing scraped data.
- **`requirements.txt`**: A list of all Python dependencies for the project.

## Contributing

Contributions are welcome! If you have any suggestions or improvements, please feel free to open an issue or submit a pull request.
