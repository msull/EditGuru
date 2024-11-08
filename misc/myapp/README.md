# MyApp

A simple Flask application demonstrating the use of Blueprints.

## Setup

1. Clone the repository.
2. Navigate to the project directory.
3. Install dependencies using `pip`:

   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

1. Start the Flask server:

   ```bash
   invoke run_server
   ```

2. Hit the example endpoint:

   ```bash
   invoke hit_endpoint
   ```

## Folder Structure

```
myapp/
├── pyproject.toml
├── requirements.txt
├── src/
│   ├── __init__.py
│   └── blueprints/
│       └── example.py
└── tasks.py
```