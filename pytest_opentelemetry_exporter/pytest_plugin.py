# pytest_otel_plugin.py

import logging
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any

import backoff
import pytest
import requests

# Shared lists to keep track of generated IDs
trace_ids = []
span_ids = []
DB_DIRECTORY = Path("otel_test_traces")
DB_FILE = DB_DIRECTORY / f"traces_{uuid.uuid4()}.sqlite3"


def get_db_connection():
    """Establish a connection to the shared SQLite database."""
    return sqlite3.connect(DB_FILE)


def save_id_to_db(table_name: str, id_value: str):
    """Save the generated ID to the specified table in the SQLite database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Insert the ID into the table
    cursor.execute("INSERT OR IGNORE INTO ? (id) VALUES (?)", (table_name, id_value))
    conn.commit()
    conn.close()


@pytest.fixture(scope="session", autouse=True)
def _setup_db() -> None:
    """Set up the database before running tests."""
    DB_DIRECTORY.mkdir(exist_ok=True)
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
    return _trace_id


@pytest.fixture
def span_id():
    """Generate a unique span_id, save it to the database, and yield it."""
    # Generate a UUID for span_id
    _span_id = str(uuid.uuid4())
    # Save it to the database beforehand
    save_id_to_db("span_ids", _span_id)
    # Append to the list for use after tests
    span_ids.append(_span_id)
    return _span_id


# Define a function with retries using exponential backoff and jitter
@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_time=10, jitter=backoff.random_jitter)
def fetch_trace_data(url: str):
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.text


def pytest_sessionfinish(session: Any, exitstatus: Any):
    """Hook that runs after the entire test session finishes."""
    # Get the endpoint from the environment variable
    endpoint = os.environ.get("PYTEST_OTEL_EXPORT_QUERY_ENDPOINT")
    if not endpoint:
        logging.warning("Environment variable PYTEST_OTEL_EXPORT_QUERY_ENDPOINT is not set.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    for trace_id in trace_ids:
        url = f"{endpoint}/api/traces/{trace_id}"
        json_data = fetch_trace_data(url)
        # Save the JSON data to the database
        cursor.execute("INSERT OR REPLACE INTO traces_data (trace_id, json_data) VALUES (?, ?)", (trace_id, json_data))

    conn.commit()
    conn.close()
