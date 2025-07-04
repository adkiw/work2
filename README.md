# Streamlit Logistics Appsas

This repository contains a Streamlit based application for logistics companies. The app manages shipments, vehicles and staff information in a single dashboard and stores all data in a local SQLite database.

Besides the Streamlit UI, the repository now provides an alternative FastAPI based web interface located in the `web_app` directory. This interface relies on DataTables for an Excel-style look and can be started locally without Streamlit. Initially it only supported shipment management but now also includes trucks, trailers, employees, groups, clients, drivers, trailer type management, trailer assignment and an audit log section with a simple login/registration system. Naujausioje versijoje taip pat galima atsisiųsti darbuotojų, grupių, klientų, vairuotojų bei priekabų specifikacijų, numatytų priekabų tipų, laukiančių registracijų ir aktyvių naudotojų sąrašus CSV formatu.

See [MIGRATION.md](MIGRATION.md) for a short summary of the migration progress.

## Setup

1. Create and activate a Python virtual environment and install the
   required packages from `requirements.txt`.
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Initialize the database. The helper function `init_db()` in `db.py` creates all required tables. It is executed automatically when running `main.py`, but you can also call it manually. The path can be overridden with the `DB_PATH` environment variable:
   ```python
   from db import init_db
   conn, cursor = init_db()  # uses main.db by default or DB_PATH if set
   ```
   The `init_db()` function now creates an `imone` column in both the
   `vilkikai` and `priekabos` tables by default. When run on an older database
   it will automatically add this column if it is missing.

3. Start the application:
   ```bash
   streamlit run main.py
   ```
   The main page displays a horizontal menu for modules such as shipments, trucks, trailers, groups, drivers, clients, employees, planning and updates.

   On Windows systems you can alternatively execute `start_work2_server.bat` to
   create the virtual environment (if missing), install dependencies and launch
   the FastAPI interface automatically. Linux users can run `start_work2_server.sh`
   which performs the same steps using Bash.

4. Alternatively you can run the FastAPI interface located in `web_app`:
   ```bash
   uvicorn web_app.main:app --reload
   ```
   This starts a local server on http://127.0.0.1:8000 without Streamlit.
   After login the home page is available at `http://127.0.0.1:8000/`.

   The web application can also be executed directly as a module:
   ```bash
   python -m web_app
   ```
   which runs the same server using built-in defaults.

5. To enable dark mode in the Streamlit UI, open the sidebar in the running app and choose **Dark** in the Theme selector.

## Naudojimas

Paleidus programą veikia prisijungimo sistema. Pirmą kartą duomenų bazėje automatiškai sukuriamas naudotojas **admin** su slaptažodžiu **admin**. Prisijungus šiuo vartotoju galima patvirtinti kitų naudotojų registracijas.

Prisijungimo formoje galima pasirinkti „Registruotis“ ir pateikti naujo vartotojo paraišką. Nauji naudotojai įrašomi su neaktyviu statusu ir negali prisijungti, kol administratorius jų nepatvirtins. Administratorius meniu skiltyje „Registracijos“ mato laukiančius vartotojus ir gali juos patvirtinti arba pašalinti.

Be superadministratoriaus, sistema leidžia priskirti ir „įmonės administratoriaus“ rolę. Tokie naudotojai gali patvirtinti tik savo įmonės darbuotojų registracijas. Patvirtintiems darbuotojams automatiškai suteikiama „user“ rolė.

## FastAPI Multi-tenant Backend

A minimal FastAPI backend is provided under `fastapi_app`. It uses PostgreSQL and SQLAlchemy.
To run it locally with Docker:

```bash
docker-compose -f fastapi_app/docker-compose.yml up --build
```

Before starting, copy `fastapi_app/.env.example` to `fastapi_app/.env` and set a
strong value for `SECRET_KEY`. Docker Compose will read this file and supply the
variable to the container. Alternatively you can export `SECRET_KEY` in your
environment.

If running without Docker, install the FastAPI dependencies first:

```bash
pip install -r fastapi_app/requirements.txt
```

The backend requires a `SECRET_KEY` used for JWT signing. Ensure the `.env` file
defines this variable before starting the API; otherwise the application will
fail to start.

The API exposes endpoints for user creation and JWT-based login.
You can quickly verify that the server is running by requesting the `/health` endpoint which returns `{"status": "ok"}`.

### Login rate limiting

Login endpoints (`/login` and `/auth/login`) are protected using [slowapi](https://github.com/laurentS/slowapi).
Each IP address is limited to **5 login attempts per minute**. In addition, failed
attempts are tracked per user email. After **5 consecutive failures**, the user
is blocked from logging in for 15 minutes.

### Database migrations

Alembic configuration lives in `fastapi_app/alembic`. To apply migrations run:

```bash
alembic -c fastapi_app/alembic.ini upgrade head
```

When models change a new migration can be generated with:

```bash
alembic -c fastapi_app/alembic.ini revision --autogenerate -m "message"
```

## Demo duomenys

Norėdami greitai išbandyti aplikaciją su pavyzdiniais įrašais, galite
automatiškai užpildyti duomenų bazę demonstraciniais duomenimis:

```bash
python seed_demo_data.py
```

Visi demo įrašai pažymėti prefiksu `DEMO_`. Juos pašalinti galima
paleidus:

```bash
python seed_demo_data.py --clear
```

