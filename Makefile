.PHONY: test

test:
	pip install -r requirements.txt
	pip install -r fastapi_app/requirements.txt
	pytest
