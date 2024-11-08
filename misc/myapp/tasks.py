from invoke import task
import requests

@task
def run_server(c):
    """Run the Flask development server."""
    c.run("flask run --app src --port 5000")

@task
def hit_endpoint(c):
    """Hit the example endpoint of the Flask app."""
    response = requests.get("http://127.0.0.1:5000/example")
    print(f"Response: {response.text}")