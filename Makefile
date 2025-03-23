.PHONY: up down rebuild logs

DOCKER_COMPOSE = docker-compose
DOCKER = docker
PROJECT_NAME = fundy

up:
	$(DOCKER_COMPOSE) up --build -d

down:
	$(DOCKER_COMPOSE) down

rebuild:
	$(DOCKER_COMPOSE) down
	$(DOCKER_COMPOSE) up --build -d

logs:
	$(DOCKER_COMPOSE) logs -f
