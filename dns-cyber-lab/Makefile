.DEFAULT_GOAL := help
.PHONY: help generate_shell_targets

# The path to your docker-compose file
DOCKER_COMPOSE_FILE := docker-compose.yml


## -- Help Section --

## This help message
## (can be triggered either by make or make help)
help:
	@printf "Usage\n";

	@awk '{ \
			if ($$0 ~ /^.PHONY: [a-zA-Z\-\_0-9\%]+$$/) { \
				helpCommand = substr($$0, index($$0, ":") + 2); \
				if (helpMessage) { \
					printf "\033[36m%-20s\033[0m %s\n", \
						helpCommand, helpMessage; \
					helpMessage = ""; \
				} \
			} else if ($$0 ~ /^[a-zA-Z\-\_0-9.\%]+:/) { \
				helpCommand = substr($$0, 0, index($$0, ":")); \
				if (helpMessage) { \
					printf "\033[36m%-20s\033[0m %s\n", \
						helpCommand, helpMessage; \
					helpMessage = ""; \
				} \
			} else if ($$0 ~ /^##/) { \
				if (helpMessage) { \
					helpMessage = helpMessage"\n                     "substr($$0, 3); \
				} else { \
					helpMessage = substr($$0, 3); \
				} \
			} else { \
				if (helpMessage) { \
					print "\n                     "helpMessage"\n" \
				} \
				helpMessage = ""; \
			} \
		}' \
		$(MAKEFILE_LIST)

## Generate shell access targets for each container and append to Makefile
generate_shell_targets: ## Generate shell access targets for containers based on docker-compose.yml
	@echo "\n# --- Auto-Generated Container Shell Access Targets ---" >> $(MAKEFILE_LIST)
	@grep 'container_name:' $(DOCKER_COMPOSE_FILE) | awk '{print $$2}' | while read container; do \
		echo "\n.PHONY: $${container}_shell" >> $(MAKEFILE_LIST); \
		echo "## Access shell of the $${container} container" >> $(MAKEFILE_LIST); \
		echo "$${container}_shell:" >> $(MAKEFILE_LIST); \
		echo "	docker exec -it $${container} /bin/sh" >> $(MAKEFILE_LIST); \
	done
	@echo "\n# --- End of Auto-Generated Targets ---" >> $(MAKEFILE_LIST)
	@echo "Shell access targets for containers have been appended to the Makefile."

## Install prerequisites (git, Docker, Docker Compose) on AWS Linux 2023 and clone/refresh the repository
install:
	@echo "=== Installing prerequisites on Amazon Linux 2023 ==="
	@echo "Updating package manager..."
	sudo dnf update -y
	@echo ""
	@echo "Installing git..."
	sudo dnf install -y git
	@echo ""
	@echo "Installing Docker..."
	sudo dnf install -y docker
	@echo ""
	@echo "Starting and enabling Docker service..."
	sudo systemctl start docker
	sudo systemctl enable docker
	@echo ""
	@echo "Installing Docker Compose..."
	sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$$(uname -s)-$$(uname -m)" -o /usr/local/bin/docker-compose
	sudo chmod +x /usr/local/bin/docker-compose
	@echo ""
	@echo "Verifying installations..."
	@git --version
	@docker --version
	@docker-compose --version
	@echo ""
	@echo "Cloning or refreshing the repository..."
	@if [ -d "../dns-course-labs" ]; then \
		echo "Repository exists, pulling latest changes..."; \
		cd ../dns-course-labs && git pull; \
	else \
		echo "Cloning repository..."; \
		cd .. && git clone https://github.com/jmanteau/dns-course-labs.git; \
	fi
	@echo ""
	@echo "=== Installation complete! ==="
	@echo "Note: You may need to add your user to the docker group:"
	@echo "  sudo usermod -aG docker \$$USER"
	@echo "Then log out and back in for the changes to take effect."

## Build all services without starting them
build:
	docker-compose -f $(DOCKER_COMPOSE_FILE) build

## Bring up all services with docker-compose up
up:
	@rm -f shared-data/dns_public_ip.txt
	docker-compose -f $(DOCKER_COMPOSE_FILE) up -d
	@echo "All services are up and running. Waiting 5s before showing the logs."
	sleep 5
	docker-compose logs --since 1m

## Stop all services with docker-compose stop
stop:
	docker-compose -f $(DOCKER_COMPOSE_FILE) stop
	@echo "All services have been stopped."

## List all containers for the docker-compose project
ls:
	docker-compose ps --format "table {{.Names}}\t{{.Image}}\t{{.State}}"

logs1:
	docker-compose logs --since 1m

logs5:
	docker-compose logs --since 5m

## Restart all services with docker-compose
restart:
	@rm -f shared-data/dns_public_ip.txt
	docker-compose down
	docker-compose up -d
	@echo "All services have been restarted."


## Clean up stopped containers, unused networks, dangling images, and build cache
destroy:
	@echo "Cleaning up stopped containers, unused networks, and dangling images..."
	docker-compose down -v --rmi all --volumes --remove-orphans
	docker system prune -f --volumes
	docker builder prune -f
	docker network prune -f

# --- Auto-Generated Container Shell Access Targets ---

.PHONY: client_shell
## Access shell of the client container
client_shell:
	docker exec -it client /bin/sh

.PHONY: dns_internal_shell
## Access shell of the dns_internal container
dns_internal_shell:
	docker exec -it dns_internal /bin/sh

.PHONY: dns_public_shell
## Access shell of the dns_public container
dns_public_shell:
	docker exec -it dns_public /bin/sh

.PHONY: c2_server_shell
## Access shell of the c2_server container
c2_server_shell:
	docker exec -it c2_server /bin/bash

.PHONY: webserver_shell
## Access shell of the webserver container
webserver_shell:
	docker exec -it webserver /bin/sh

.PHONY: firewall_shell
## Access shell of the firewall container
firewall_shell:
	docker exec -it firewall /bin/sh

# --- End of Auto-Generated Targets ---
