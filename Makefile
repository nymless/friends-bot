# Переменные
PYTHON := uv run python
PYTEST := uv run pytest
MYPY := uv run mypy

.PHONY: help install run test typing clean prod-install

help: ## Показать справку
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Установить все зависимости (включая dev)
	uv sync

prod-install: ## Установить все зависимости (без dev)
	uv sync --no-dev

run: ## Запустить бота из корня
	$(PYTHON) -m friends_bot.main

test: ## Запустить тесты
	$(PYTEST) tests/

typing: ## Проверить типизацию через mypy
	$(MYPY) src

clean: ## Удалить временные файлы, кэш и окружение
	rm -rf `find . -name __pycache__`
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .venv
