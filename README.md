# 🔧 Hardware Sourcing & Specs Agent

> **An autonomous AI agent that researches electronic components** — finds datasheets, compares distributor pricing, validates stock availability, and returns a structured report. Built with LangGraph, Pydantic, and Streamlit.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph-green.svg)](https://github.com/langchain-ai/langgraph)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-red.svg)](https://docs.pydantic.dev/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-ff4b4b.svg)](https://streamlit.io/)

---

## 🎯 Problem Statement

Hardware engineers routinely spend **30–60 minutes per component** cross-referencing datasheets, comparing distributor prices, and verifying stock availability. This agent automates the entire workflow:

**Input:** A component name (e.g., `ESP32-WROOM-32`)
**Output:** A structured JSON report with manufacturer info, datasheet link, key pins, pricing comparison, and stock status.

---

## ✨ Features

- **4 Autonomous Tools**: Web search (Tavily), LLM-powered datasheet extraction, pricing lookup, stock validation
- **Agentic Reasoning Loop**: LangGraph `StateGraph` with 6 nodes, conditional edges, and retry cycles
- **Strict Data Validation**: Pydantic v2 models at every boundary
- **Real-time Dashboard**: Streamlit UI with progress tracking, pricing charts, and pin tables
- **Agent Reasoning Trace**: Full transparency — see every decision the agent makes
- **20+ Component Database**: Mock pricing for popular components ensures reliable demos
- **Retry & Error Handling**: Automatic retries with graceful degradation
- **Caching**: In-memory TTL cache to avoid redundant API calls

---

## 🏗️ Architecture

The agent uses a custom **LangGraph StateGraph** (not `create_react_agent`) to demonstrate explicit control over the agentic reasoning loop:

```
START → Planner → Searcher → Extractor → Pricing → Validator → Formatter → END
                     ↑                                    |
                     |←────── retry (max 2) ──────────────|
                                                          |
                     Error Handler ←─── (exhausted) ──────|
                          |
                          ↓
                         END
```

### Node Descriptions

| Node | Responsibility | Tools Used |
|------|---------------|------------|
| **Planner** | Analyzes query, creates research strategy | LLM reasoning |
| **Searcher** | Executes web searches for datasheets & specs | Tavily Search |
| **Extractor** | Extracts structured data from search results | LLM + Pydantic |
| **Pricing** | Looks up distributor pricing | Mock API + Cache |
| **Validator** | Checks stock availability, validates completeness | Aggregation logic |
| **Formatter** | Compiles final structured report | Pydantic serialization |

---

## 🚀 Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/hardware-sourcing-agent.git
cd hardware-sourcing-agent

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
# Copy the example env file
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac
```

Edit `.env` and add your API keys:
- **Tavily API Key** (free tier: 1000 searches/month): [tavily.com](https://tavily.com)
- **Google Gemini API Key** (free tier available): [aistudio.google.com](https://aistudio.google.com/app/apikey)

### 3. Run (CLI)

```bash
python -m src.main "ESP32-WROOM-32"
```

### 4. Run (Streamlit Dashboard)

```bash
streamlit run app.py
```

---

## 📸 Usage Examples

### CLI Output

```bash
$ python -m src.main "ESP32-WROOM-32"

============================================================
  Hardware Sourcing & Specs Agent
  Component: ESP32-WROOM-32
============================================================

  Component:    ESP32-WROOM-32
  Manufacturer: Espressif Systems
  Description:  Wi-Fi & Bluetooth MCU module based on ESP32 chip
  Datasheet:    https://www.espressif.com/.../esp32-wroom-32_datasheet_en.pdf
  Package:      SMD Module (18x25.5mm)
  Voltage:      2.2V - 3.6V

  --- Key Pins (5) ---
    Pin    2 | VCC          | Power Supply 3.3V
    Pin    1 | GND          | Ground
    Pin   25 | GPIO0        | General Purpose I/O / Boot Mode
    Pin   35 | TX0          | UART0 Transmit
    Pin   34 | RX0          | UART0 Receive

  --- Pricing ---
  Average:    $3.12
  Range:      $2.80 - $3.45
  Best Deal:  Mouser @ $2.80 (MOQ: 1)

  Distributor               Price     MOQ      Stock
  -------------------------------------------------------
  Mouser Electronics        $  2.80      1     14,523
  DigiKey                   $  3.10      1      8,920
  Newark / Farnell          $  3.45      1      3,210

  Stock: IN STOCK (Total: 26,653 units)
```

### Streamlit Dashboard

The dashboard provides:
- Real-time agent progress tracking
- Interactive component info card
- Pricing comparison bar chart
- Pin summary table
- Agent reasoning trace timeline
- Raw JSON output

---

## 📁 Project Structure

```
├── README.md                      # This file
├── requirements.txt               # Python dependencies
├── .env.example                   # API key template
├── .gitignore                     # Git ignore rules
├── app.py                         # Streamlit dashboard
│
├── src/
│   ├── __init__.py
│   ├── main.py                    # CLI entry point
│   ├── agent.py                   # LangGraph StateGraph (core)
│   ├── state.py                   # Pydantic models & state schema
│   ├── tools/
│   │   ├── tavily_search.py       # Tavily web search tool
│   │   ├── datasheet_extractor.py # LLM-powered extraction
│   │   ├── pricing_lookup.py      # Distributor pricing (mock)
│   │   └── stock_validator.py     # Stock availability check
│   ├── data/
│   │   └── mock_pricing.json      # Pricing database (20+ components)
│   └── utils/
│       ├── logger.py              # Loguru configuration
│       └── cache.py               # In-memory TTL cache
│
└── tests/
    ├── test_models.py             # Pydantic model tests
    └── test_agent.py              # Integration & e2e tests
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Orchestration** | LangGraph `StateGraph` | Stateful agent graph with conditional edges |
| **LLM** | Google Gemini 2.0 Flash | Structured data extraction (free tier) |
| **Search** | Tavily API | AI-optimized web search |
| **Validation** | Pydantic v2 | Strict data contracts at all boundaries |
| **UI** | Streamlit | Interactive dashboard with real-time updates |
| **HTTP** | Requests + BeautifulSoup | HTTP client + HTML parsing |
| **Logging** | Loguru | Colored console + rotating file logs |
| **Config** | python-dotenv | Environment variable management |

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run model tests only
pytest tests/test_models.py -v

# Run integration tests (requires API keys)
pytest tests/test_agent.py -v
```

---

## ⚠️ Limitations & Future Work

### Current Limitations
1. **Mock Pricing Data**: Uses a JSON file instead of real distributor APIs. Real APIs (DigiKey, Mouser) require OAuth registration that takes several days to approve.
2. **Single Component**: Processes one component at a time (no batch/comparison mode).
3. **LLM Dependency**: Datasheet extraction quality depends on the LLM's knowledge of the component.

### Future Improvements
1. **Real Distributor APIs**: Integrate DigiKey and Mouser APIs for live pricing
2. **Component Comparison**: Side-by-side comparison of 2-3 alternative components
3. **PDF Parsing**: Download and parse actual datasheet PDFs for pin diagrams
4. **Conversation Mode**: Follow-up questions about component compatibility
5. **Export**: CSV/Excel export for procurement teams
6. **Memory**: Persistent session history using LangGraph checkpointing

---

## 🏆 Bonus Technologies Used

- ✅ **LangGraph** — Full `StateGraph` with conditional edges and retry cycles
- ✅ **Pydantic v2** — Strict validation models at every data boundary
- ✅ **Built with Antigravity** — AI-assisted development

---

## 📄 License

This project was built as a submission for the Lumiq.ai internship assignment.

---

*Built with ❤️ using LangGraph, Pydantic, and Streamlit*
#   H a r d w a r e _ c o m p o n e n t _ s e a r c h _ e n g i n e  
 