.PHONY: run start test build-frontend

run start:
	@./iniciar.sh

test:
	@PYTHONPATH=backend ./venv/bin/pytest -v

build-frontend:
	@cd frontend && npm run build
