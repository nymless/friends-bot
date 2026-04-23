# Переменные
PYTHON := uv run python
PYTEST := uv run pytest
MYPY := uv run mypy
RUFF := uv run ruff

.PHONY: install prod-install run test type lint format clean

install: ## Установить все зависимости (включая dev)
	uv sync

prod-install: ## Установить все зависимости (без dev)
	uv sync --no-dev

run: ## Запустить бота
	$(PYTHON) -m src.friends_bot.main

test: ## Запустить тесты
	$(PYTEST) tests/

type: ## Проверить типизацию через mypy
	$(MYPY) src

lint: ## Проверить код на ошибки и стиль через Ruff
	$(RUFF) check src

format: ## Автоматически поправить стиль и импорты
	$(RUFF) format src
	$(RUFF) check --fix src

clean: ## Удалить временные файлы, кэш и окружение
	rm -rf `find . -name __pycache__`
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf .venv
