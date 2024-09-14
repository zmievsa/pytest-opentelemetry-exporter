# pytest_otel_plugin.py

import os
import sqlite3
import uuid

import backoff
import pytest
import requests

# Shared lists to keep track of generated IDs
trace_ids = []
span_ids = []


def get_db_connection():
    """Establish a connection to the shared SQLite database."""
    db_path = "shared_data.db"  # Path to your shared SQLite database
    conn = sqlite3.connect(db_path)
    return conn


def save_id_to_db(table_name, id_value):
    """Save the generated ID to the specified table in the SQLite database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Insert the ID into the table
    cursor.execute(f"INSERT OR IGNORE INTO {table_name} (id) VALUES (?)", (id_value,))
    conn.commit()
    conn.close()


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Set up the database before running tests."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Create the tables if they don't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trace_ids (
            id TEXT PRIMARY KEY
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS span_ids (
            id TEXT PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()


@pytest.fixture
def trace_id():
    """Generate a unique trace_id, save it to the database, and yield it."""
    # Generate a UUID for trace_id
    _trace_id = str(uuid.uuid4())
    # Save it to the database beforehand
    save_id_to_db("trace_ids", _trace_id)
    # Append to the list for use after tests
    trace_ids.append(_trace_id)
    yield _trace_id


@pytest.fixture
def span_id():
    """Generate a unique span_id, save it to the database, and yield it."""
    # Generate a UUID for span_id
    _span_id = str(uuid.uuid4())
    # Save it to the database beforehand
    save_id_to_db("span_ids", _span_id)
    # Append to the list for use after tests
    span_ids.append(_span_id)
    yield _span_id


# Define a function with retries using exponential backoff and jitter
@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_time=10, jitter=backoff.random_jitter)
def fetch_trace_data(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text


def pytest_sessionfinish(session, exitstatus):
    """Hook that runs after the entire test session finishes."""
    # Get the endpoint from the environment variable
    endpoint = os.environ.get("PYTEST_OTEL_EXPORT_QUERY_ENDPOINT")
    if not endpoint:
        print("Environment variable PYTEST_OTEL_EXPORT_QUERY_ENDPOINT is not set.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    for trace_id in trace_ids:
        url = f"{endpoint}/api/traces/{trace_id}"
        try:
            json_data = fetch_trace_data(url)
            # Save the JSON data to the database
            cursor.execute(
                "INSERT OR REPLACE INTO traces_data (trace_id, json_data) VALUES (?, ?)", (trace_id, json_data)
            )
        except requests.RequestException as e:
            print(f"Error fetching trace data for trace_id {trace_id}: {e}")

    conn.commit()
    conn.close()
