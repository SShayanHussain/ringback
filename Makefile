# Ringback dev shortcuts. Text-first — nothing here spends voice minutes.
.PHONY: help up down agent-install agent-test orchestrator-test test evals playground lint web-dev

help:
	@echo "up             - docker compose up (pg + redis + agent-core + orchestrator + web)"
	@echo "down           - docker compose down"
	@echo "agent-install  - pip install the agent + orchestrator (editable) for local runs"
	@echo "agent-test     - pytest the conversation core"
	@echo "test           - pytest agent + orchestrator"
	@echo "evals          - python -m evals.run  (the Phase 3 gate before voice)"
	@echo "playground     - free text REPL against the agent core (no voice spend)"
	@echo "lint           - ruff check (python) + next lint (web)"

up:
	docker compose up --build

down:
	docker compose down

agent-install:
	pip install -e ./agent -e ./orchestrator
	pip install pytest ruff

agent-test:
	cd agent && pytest -q

orchestrator-test:
	cd orchestrator && pytest -q

test: agent-test orchestrator-test

evals:
	cd agent && python -m evals.run

playground:
	cd agent && python -m ringback_agent.playground

lint:
	ruff check agent orchestrator
	npm run lint --workspace web
