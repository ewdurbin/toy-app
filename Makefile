.PHONY: dev clean

dev:
	docker compose --env-file .dev.env up --build

clean:
	docker compose --env-file .dev.env down -v
	rm -rf app/node_modules app/dist
	rm -rf server/.venv
	find server -type d -name __pycache__ -exec rm -rf {} +
