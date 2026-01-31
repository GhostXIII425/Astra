# Astra - Personal Finance Application

Astra is a local-first, cross-platform personal finance application built with Python and Dear PyGui.

## Features
- **User Isolation:** Each user's data is stored in a separate SQLite database.
- **Security:** Passwords are hashed with `bcrypt`. Sensitive transaction data is encrypted at rest using `cryptography`.
- **ML Categorization:** Automatic transaction categorization using a user-specific k-NN model.
- **Multi-format Import:** Supports CSV, Excel, and plain-text bank statements.

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

To run the backend tests:
```bash
pytest astra/tests/
```

## Project Structure
- `astra/backend/`: Core logic (Auth, Storage, ML, Parsing).
- `astra/frontend/`: Dear PyGui UI implementation.
- `astra/tests/`: Unit and integration tests.
