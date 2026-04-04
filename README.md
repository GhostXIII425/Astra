# Astra - Personal Finance Application

Astra is a local-first, offline-first personal finance application built with Python and Dear PyGui.

## Features
- **Offline-First:** All data is stored locally in a single SQLite database (`astra_local.db`).
- **Security:** Sensitive transaction data and account numbers are encrypted at rest using AES-128 via `cryptography`.
- **Rule-Based Intelligence:** Automated transaction categorization based on customizable keyword rules.
- **Multi-format Import:** Supports CSV, Excel, and plain-text bank statements with an interactive mapping UI.
- **Budgeting:** Supports custom budget periods (monthly, biweekly, weekly) and rollover rules.
- **Multi-Account:** Support for multiple account types including Cash, Checking, Credit, Envelope, and Savings.
- **GUI Features:** Debug console, theme customization (Light/Dark mode), and hotkeys (Ctrl+R for refresh).

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

To start the application:
```bash
python3 -m astra.frontend.dearpygui.main
```

## Running Tests

To run the tests:
```bash
python3 -m pytest astra/tests/
```

## Project Structure
- `astra/backend/`: Core logic (Storage, Parsing, Intelligence).
- `astra/frontend/`: Dear PyGui UI implementation.
- `astra/tests/`: Unit and integration tests.
