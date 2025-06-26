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

## Naudojimas

Paleidus programą veikia prisijungimo sistema. Pirmą kartą duomenų bazėje automatiškai sukuriamas naudotojas **admin** su slaptažodžiu **admin**. Prisijungus šiuo vartotoju galima patvirtinti kitų naudotojų registracijas.

Prisijungimo formoje galima pasirinkti „Registruotis“ ir pateikti naujo vartotojo paraišką. Nauji naudotojai įrašomi su neaktyviu statusu ir negali prisijungti, kol administratorius jų nepatvirtins. Administratorius meniu skiltyje „Registracijos“ mato laukiančius vartotojus ir gali juos patvirtinti arba pašalinti.

## FastAPI Multi-tenant Backend

A minimal FastAPI backend is provided under `fastapi_app`. It uses PostgreSQL and SQLAlchemy.
To run it locally with Docker:

```bash
docker-compose -f fastapi_app/docker-compose.yml up --build
```

The API exposes endpoints for tenant and user management using JWT tokens.
Example workflow:
1. Create a tenant as superadmin via `POST /superadmin/tenants`.
2. Assign a tenant admin using `POST /superadmin/tenants/{tenant_id}/admins`.
3. Tenant admins can create users in their tenant via `POST /{tenant_id}/users`.
4. Users authenticate using `/auth/login` and may refresh tokens via `/auth/refresh`.
