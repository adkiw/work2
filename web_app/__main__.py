from uvicorn import run

# Import string notation is required for reload to work
APP_IMPORT = "web_app.main:app"

if __name__ == "__main__":
    # Pass the application as an import string so `reload` works
    run(APP_IMPORT, host="127.0.0.1", port=8000, reload=True)

