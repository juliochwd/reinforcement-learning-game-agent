# Copilot Instructions for Advanced Ensemble Game Agent

## Architecture Overview

This is an **Advanced Ensemble Machine Learning System** for game prediction with integrated data scraping capabilities. Originally a reinforcement learning project, it has evolved into a sophisticated supervised learning system with **anti-leakage guarantees** and real-time prediction capabilities targeting **Big/Small** classification (Number > 4 = Big, 0-4 = Small).

### Core Components & Data Flow

```
Entry Points:
  main.py (GUI) → TaskOrchestrator → AdvancedEnsemble → SRPClassifier/TreeClassifier
  scraper_shell.py (CLI) → MockQueue → RealtimeAgent → BrowserManager + DataScraper
  start.py (Menu) → Interactive Selection → All Operations
       ↓               ↓                    ↓              ↓
  config.yaml → GUI/Console → Browser/ML → API/Training → CSV/Predictions
```

**Key Files:**
- `main.py`: GUI entry point with ensemble ML and scraping capabilities  
- `scraper_shell.py`: Command-line entry point with optional Gemini 2.5 Flash AI
- `start.py`: Cross-platform interactive menu for all operations
- `config.yaml`: Central configuration for selectors, timeouts, ML strategies, and anti-leakage settings
- `src/app/gui.py`: CustomTkinter GUI with ML training, monitoring, and prediction tabs
- `src/app/task_orchestrator.py`: Threading manager for GUI and ML operations
- `src/rl_agent/realtime_agent.py`: Main orchestrator for scraping operations
- `src/rl_agent/browser_manager.py`: Selenium WebDriver lifecycle management
- `src/rl_agent/data_scraper.py`: Core scraping logic with API interception
- `src/rl_agent/gemini_predictor.py`: Google Gemini 2.5 Flash with thinking capabilities

### Execution Modes

**GUI Mode (Machine Learning + Scraping):**
```bash
python main.py  # Full GUI with ML training, prediction, and scraping tabs
```

**Shell Mode (Enhanced with AI):**
```bash
python scraper_shell.py --mode bulk --phone 1234567890
python scraper_shell.py --mode live --model gemini-2.5-flash  # With AI analysis
```

**Interactive Menu (Recommended):**
```bash
python start.py  # Cross-platform menu system for all operations
start.bat        # Windows batch launcher (14 integrated functions)
```

**Specialized Launchers:**
- `setup.bat` - One-time environment setup
- `run_bulk_scrape.bat` - Simple bulk data collection  
- `run_live_scrape.bat` - Live monitoring with auto-stop
- `set_credentials.bat` - Environment variable management

## Development Patterns

### Anti-Leakage Machine Learning Architecture
- **PRIMARY TARGET**: Big/Small classification (Number > 4 = Big, 0-4 = Small)
- **NO DATA LEAKAGE**: Chronological splits, lag-only features, no future data in training
- **FORBIDDEN FEATURES**: Premium, Color, streak, correlation, wavelet - only use `engineer_features_number_full_anti_leakage()`
- **ENSEMBLE STRATEGIES**: SRPClassifier (primary), ExtremelyFastDecisionTreeClassifier (speed), LogisticRegression (stable)
- **AUTOMATED AUDITING**: Anti-leakage validation, performance monitoring, rollback on drift

### Advanced Ensemble Configuration
```python
# Strategy selection in config.yaml
ensemble:
  strategy: 'srp'  # Primary: Streaming Random Patches
  fallback_strategy: 'fast_decision_tree'  # Speed fallback
  gaming_mode: 'speed_balanced'  # Ultra-fast prediction (<2ms)
  auto_optimization: true
```

### Gemini 2.5 Flash Integration Pattern
```python
# Enhanced thinking capabilities in GeminiPredictor
generation_config = types.GenerationConfig(
    thinking_config=types.ThinkingConfig(
        thinking_budget=-1,
        include_thoughts=True
    )
)
# Outputs: "--- THOUGHTS ---" and "--- PREDICTION ---" sections
```

### Configuration-Driven Architecture
- **ALL selectors, timeouts, and URLs are in `config.yaml`** - never hardcode XPaths
- Use `_get_selector(category, name)` pattern to retrieve XPath configs
- Example: `self._get_selector('login', 'user_input')` returns `(By.NAME, "userNumber")`
- Shell and GUI modes share identical configuration

### Threading & Communication
- **GUI Mode**: GUI operations in main thread; use `gui_queue` for cross-thread communication
- **Shell Mode**: Uses `MockQueue` class to simulate GUI queue interface
- TaskOrchestrator wraps operations in `run_in_thread()` to prevent blocking
- Progress updates: `logging.info("X/Y")` → ModernProgressbarHandler → display

### Browser Management Pattern
```python
# Always use BrowserManager for driver lifecycle
driver = self.browser_manager.initialize_driver()
if not self.browser_manager.login(phone, password):
    return False
# DataScraper handles the actual scraping operations
```

### Path Setup Convention
Every module starts with:
```python
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
```

### Credential Management
- **Environment Variables**: Preferred method using `PHONE_NUMBER`, `PASSWORD`, and `GEMINI_API_KEY`
- **Command Line Args**: `--phone` and `--password` parameters
- **Interactive Prompts**: Secure input when no credentials provided
- **No Storage**: Credentials never persisted in code or config files
- **AI Integration**: Gemini API key required for `--model` functionality

## Critical Implementation Details

### Selenium-Wire for API Interception
- Uses `selenium-wire` not standard `selenium` - enables request/response capture
- Primary data collection method: `driver.wait_for_request(api_endpoint)` 
- Fallback to UI scraping if API interception fails

### XPath Configuration System
- Selectors support multiple strategies: `by: "XPATH"/"NAME"/"CLASS_NAME"` 
- Complex selectors use relative paths: `./div` for child elements
- All timeouts configurable per operation type

### Auto-Stop Mechanisms (Live Scraping)
- **Time Limit**: `live_timeout_minutes: 30` in config (max runtime)
- **Iteration Limit**: `max_live_iterations: 100` (max cycles)
- **Empty Response Limit**: 50 consecutive empty API responses
- Prevents infinite loops in continuous monitoring mode

### Data Processing Pipeline
- **Primary Pipeline**: `engineer_features_number_full_anti_leakage()` (75+ features: lag, rolling, fourier, spectral)
- **Target Processing**: Big/Small classification with automated audit validation
- Data filtered for game type '10001' (Win Go 1min)
- Output format: CSV with 'Period' and 'Number' columns
- Default output: `data/databaru_from_api.csv`
- **Anti-Leakage Reports**: Automated generation with security validation

### MCP Integration (Model Context Protocol)
- **Configuration**: `.cursor/mcp.json` with context7, sequential-thinking, firecrawl-mcp
- **Enhanced Context**: Pieces and supermemory integrations for development
- **AI Development**: Supports advanced reasoning and context-aware coding assistance

### Gemini AI Integration (Optional)
- **GeminiPredictor**: Real-time analysis using Google's Gemini 2.5 Flash models
- **Thinking Mode**: Enhanced reasoning with thought processes exposed (`include_thoughts=True`)
- **Environment Setup**: Requires `GEMINI_API_KEY` in environment variables
- **System Instructions**: Loads from `gemini_gems/petunjuk_gemini.md` and `gemini_gems/KODEKS_FINAL_PREDIKSI.md`
- **Live Mode Integration**: Automatic report generation on new data events
- **MockQueue Enhancement**: Shell mode MockQueue triggers AI analysis when `--model` specified
- **Dual Output Format**: "--- THOUGHTS ---" and "--- PREDICTION ---" sections for transparency

## Development Workflows

### Shell Mode Development
```bash
# All operations now centralized through start.bat
start.bat

# Direct Python execution (advanced users)
python scraper_shell.py --mode bulk --phone 82284608240
python scraper_shell.py --mode live --model gemini-2.5-flash
python scraper_shell.py --mode fetch --url "https://api.example.com/data"

# Emergency operations
stop_live_scraping.bat
```

### Machine Learning Development Workflow
```bash
# Quick ensemble testing
python quick_start.py

# Full training pipeline with anti-leakage validation
python main.py  # Use Training tab in GUI

# Advanced ensemble benchmarking
python demo_ensemble.py

# Migration from legacy models
python migrate_ensemble.py
```

### Adding New Scraping Features
1. Add XPath selectors to `config.yaml` under appropriate category
2. Implement logic in `DataScraper` class using `_get_selector()` pattern
3. Update `RealtimeAgent` to orchestrate new functionality
4. **For GUI**: Add controls in `gui.py` with proper threading via `TaskOrchestrator`
5. **For Shell**: Extend `scraper_shell.py` with new command-line arguments
6. **For AI Enhancement**: Update `MockQueue` in shell mode to trigger analysis if needed

### Adding Machine Learning Features
1. **Ensemble Strategies**: Add new strategies to `src/app/ensemble_config.py` 
2. **Feature Engineering**: Only modify `engineer_features_number_full_anti_leakage()` - other functions are deprecated
3. **Anti-Leakage Validation**: Run automated auditing after any ML changes
4. **Performance Monitoring**: Use built-in drift detection and rollback mechanisms
5. **Testing**: Use `quick_start.py` for rapid iteration and validation

### Adding AI Analysis Features
1. Update system instructions in `gemini_gems/` directory for specialized prompts
2. Extend `GeminiPredictor` class with new analysis methods
3. Modify `MockQueue.put()` in shell mode to trigger appropriate AI responses
4. Test with `--model gemini-2.5-flash` parameter

### Debugging Selenium Issues
- Check `logs/performance.log` for detailed operation logs
- Selenium errors often require XPath updates in `config.yaml`
- Use `WebDriverWait` with configurable timeouts from config
- Shell mode provides cleaner console output for debugging

### Configuration Changes
- UI settings: `config.yaml` → `ui` section
- Web selectors: `config.yaml` → `xpaths` section  
- Performance tuning: `config.yaml` → `timeouts`/`timers` sections
- Auto-stop limits: `config.yaml` → `web_agent.scraping` section

## Important Conventions

- **No direct Selenium commands in GUI code** - always delegate to TaskOrchestrator
- **Shell mode uses MockQueue** - maintains compatibility with existing agent code
- **All user interactions require credential input** - no stored passwords
- **Progress tracking via logging messages** - use "X/Y" format for auto-parsing
- **Error handling must not crash GUI thread** - wrap in try/catch with logging
- **Module imports after path setup** - avoid import errors in nested structure
- **Auto-stop conditions required** - prevent infinite processes in live mode
- **AI integration is optional** - system must work without Gemini API key
- **Configuration-first principle** - all settings externalized to `config.yaml`

## AI Enhancement Patterns

### Gemini Integration Architecture
```python
# Initialize predictor in shell mode only when --model specified
if gemini_model:
    self.gemini_predictor = GeminiPredictor(model_name=gemini_model)

# Enhanced MockQueue with AI trigger
class MockQueue:
    def put(self, item):
        if isinstance(item, dict) and item.get('type') == 'new_data' and self.predictor:
            report = self.predictor.generate_holistic_report(str(item.get('data')))
            print(f"\n--- GEMINI REPORT ---\n{report}\n")
```

### System Instructions Pattern
- AI behavior defined in `gemini_gems/petunjuk_gemini.md` (core philosophy)
- Domain knowledge in `gemini_gems/KODEKS_FINAL_PREDIKSI.md` (prediction protocols)
- Combined as system instruction for model initialization
- Follows "constitution + knowledge" architecture for AI consistency

## Shell Mode Integration
- **Centralized Control**: All operations unified through `start.bat` menu system
- **14 Integrated Functions**: Scraping, AI analysis, data management, system utilities
- **Full Compatibility**: Shell execution maintains compatibility with existing codebase
- **Smart Credential Management**: Environment variables, interactive prompts, secure storage
- **Emergency Controls**: Stop utilities, backup systems, comprehensive logging
- **AI Integration**: Optional Gemini AI analysis with real-time and batch modes
- **Data Utilities**: External data fetching, viewing, backup, and analysis features

## Data Output
- Default output: `data/databaru_from_api.csv`
- Format: Period (game ID), Number (result)
- Filtering: Only Win Go 1min games (period contains '10001')

## Data Output
- Default output: `data/databaru_from_api.csv`
- Format: Period (game ID), Number (result)
- Filtering: Only Win Go 1min games (period contains '10001')
