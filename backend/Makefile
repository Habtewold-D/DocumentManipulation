COMPOSE_FILE=../docker-compose.backend.yml

.PHONY: dev-up dev-down dev-logs dev-ps dev-rebuild

dev-up:
	docker compose -f $(COMPOSE_FILE) up

dev-rebuild:
	docker compose -f $(COMPOSE_FILE) up --build

dev-down:
	docker compose -f $(COMPOSE_FILE) down

dev-logs:
	docker compose -f $(COMPOSE_FILE) logs -f backend-api backend-worker redis

dev-ps:
	docker compose -f $(COMPOSE_FILE) ps