.PHONY: clean install lint format test build publish dev-install

# Default target
all: clean install lint test

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .ruff_cache
	rm -rf .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Install package in development mode
install:
	pip install -e ".[dev]"

# Run linting
lint:
	ruff check .

# Format code
format:
	ruff format .

# Run tests
test:
	pytest

# Build package
build: clean
	python -m build

# Publish to PyPI
publish: build
	twine upload dist/*

publish-test: build
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# Install development dependencies
dev-install:
	pip install -e ".[dev]"
	pre-commit install

# Run the package
run:
	python -m linkedin_games_scraper
