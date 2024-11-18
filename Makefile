# Variables
IMAGE_NAME := silencer
VERSION := 0.1.4
DOCKER_REPO := mrkaran

# Local Development
.PHONY: install
install:
	pip install -r requirements.txt

.PHONY: run
run:
	python main.py

# Docker Commands
.PHONY: docker-build
docker-build:
	docker build -t $(IMAGE_NAME):$(VERSION) .
	docker tag $(IMAGE_NAME):$(VERSION) $(IMAGE_NAME):latest

.PHONY: docker-run
docker-run:
	docker run -p 7788:7788 \
		-e MATTERMOST_TOKEN=${MATTERMOST_TOKEN} \
		-e ALERTMANAGER_URL=${ALERTMANAGER_URL} \
		$(IMAGE_NAME):latest

# Docker Publishing
.PHONY: docker-login
docker-login:
	docker login

.PHONY: docker-tag
docker-tag:
	docker tag $(IMAGE_NAME):$(VERSION) $(DOCKER_REPO)/$(IMAGE_NAME):$(VERSION)
	docker tag $(IMAGE_NAME):$(VERSION) $(DOCKER_REPO)/$(IMAGE_NAME):latest

.PHONY: docker-push
docker-push: docker-tag
	docker push $(DOCKER_REPO)/$(IMAGE_NAME):$(VERSION)
	docker push $(DOCKER_REPO)/$(IMAGE_NAME):latest

# Full Release Process
.PHONY: release
release: docker-build docker-login docker-push
