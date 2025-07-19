# Standard Workflows for Cline

### Workflow 1: Adding a New Scraping Feature

1.  **Goal**: Add functionality to scrape a new data point (e.g., user's current balance).
2.  **Step 1: Update Config**
    -   Cline uses `replace_in_file` to add a new selector to `config.yaml` under an appropriate category (e.g., `xpaths.dashboard.balance_element`).
3.  **Step 2: Implement Scraping Logic**
    -   Cline modifies `src/rl_agent/data_scraper.py` to add a new method (e.g., `get_balance(self)`) that uses the new selector.
4.  **Step 3: Orchestrate Logic**
    -   Cline modifies `src/rl_agent/realtime_agent.py` to call the new `data_scraper` method.
5.  **Step 4: Integrate with Shell**
    -   Cline modifies `scraper_shell.py` to add a new command or option that triggers the new functionality.
6.  **Step 5: Test**
    -   Cline uses `execute_command` with `start.bat` to run the corresponding shell command and verify the new data is scraped correctly.

### Workflow 2: Adding an AI Analysis Feature

1.  **Goal**: Create a new AI-powered report based on scraped data.
2.  **Step 1: Update AI Prompts**
    -   Cline modifies the system instructions in `gemini_gems/petunjuk_gemini.md` or `gemini_gems/KODEKS_FINAL_PREDIKSI.md` to define the new analysis task.
3.  **Step 2: Extend AI Predictor**
    -   Cline modifies `src/rl_agent/gemini_predictor.py` to add a new method (e.g., `generate_balance_report(self, data)`) that calls the Gemini API with the new instructions.
4.  **Step 3: Integrate with Shell Trigger**
    -   Cline modifies the `MockQueue` class in `scraper_shell.py`. The `put` method is updated to recognize a new data type or condition and call the new `gemini_predictor` method.
5.  **Step 4: Test**
    -   Cline uses `execute_command` to run a live scrape via `start.bat`, ensuring the `--model` parameter is included.
    -   `start.bat` -> `python scraper_shell.py --mode live --model [model_name]`
    -   Cline verifies that the new AI report is printed to the console when the relevant data is detected.

### Workflow 3: Fixing a Broken Selector

1.  **Goal**: The login button selector has changed, causing login to fail.
2.  **Step 1: Identify Failure**
    -   Cline runs a scraping task via `start.bat` and observes from the logs that it fails with a `TimeoutException` or `NoSuchElementException`.
3.  **Step 2: Propose Fix**
    -   Cline informs the user about the likely cause (a changed selector) and asks for the updated XPath or other locator.
4.  **Step 3: Update Config**
    -   Once the user provides the correct selector, Cline uses `replace_in_file` to update the relevant entry in `config.yaml`.
5.  **Step 4: Verify Fix**
    -   Cline re-runs the same scraping task using `start.bat` and confirms that the process now proceeds past the point of failure.
