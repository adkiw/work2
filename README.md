# Streamlit Logistics App

This repository contains a Streamlit based application for logistics companies. The app manages shipments, vehicles and staff information in a single dashboard and stores all data in a local SQLite database.

## Setup

1. Create and activate a Python virtual environment.
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install streamlit pandas
   ```

2. Initialize the database. The helper function `init_db()` in `db.py` creates all required tables. It is executed automatically when running `main.py`, but you can also call it manually:
   ```python
   from db import init_db
   conn, cursor = init_db()  # uses main.db by default
   ```

3. Start the application:
   ```bash
   streamlit run main.py
   ```
   The main page displays a horizontal menu for modules such as shipments, trucks, trailers, groups, drivers, clients, employees, planning and updates.

## Planned authentication

Authentication has not been implemented yet. A simple login system is planned so that only authorized employees will be able to view and modify data once the feature is added.
