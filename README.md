# LinkedIn Games Scraper

A Python package that automatically solves LinkedIn games by extracting solutions from network requests.

## Features

- Solves all LinkedIn daily games:
  - Pinpoint
  - CrossClimb
  - Queens
  - Zip
  - Tango
  - Mini Sudoku
- Headless operation (no browser window required)
- Saves solutions to JSON files
- Simple API for integration into other projects

## Installation

```bash
pip install linkedin_games_scraper
```

## Requirements

- Python 3.6+
- Chrome browser installed
- ChromeDriver compatible with your Chrome version

## Usage

### Command Line

After installation, you can run the scraper from the command line:

```bash
linkedin-games-solver
```

This will solve all LinkedIn games and save the results to a JSON file in the `results` directory.

### Python API

#### Solving All Games

```python
from linkedin_games_scraper import GameSolver

# Create a solver instance
solver = GameSolver(headless=True)

# Solve all games
results = solver.solve_all_games()

# Results will contain solutions for all games
print(results)
```

#### Solving a Specific Game

```python
from linkedin_games_scraper import GameSolver

# Create a solver instance
solver = GameSolver(headless=True)

try:
    # Solve Pinpoint
    pinpoint_solution = solver.solve_pinpoint()
    print(f"Pinpoint solution: {pinpoint_solution}")

    # Solve CrossClimb
    crossclimb_solution = solver.solve_crossclimb()
    print(f"CrossClimb solution: {crossclimb_solution}")

    # Other games: solve_zip(), solve_queens(), solve_tango(), solve_mini_sudoku()
finally:
    # Always clean up to close the browser and save results
    results_file = solver.cleanup()
    print(f"Results saved to {results_file}")
```

#### Customising the Results Directory

```python
from linkedin_games_scraper import GameSolver

# Specify a custom results directory
solver = GameSolver(headless=True, results_dir="my_solutions")

# Solve games...
solver.solve_all_games()
```

### Timeouts and Logging

All game solvers use a per-game timeout of 30 seconds by default and produce detailed logs while navigating, switching iframes, clicking the start button, scanning network requests, and extracting solutions.

You can override the timeout per solver method if needed, for example:

```python
from linkedin_games_scraper import GameSolver

solver = GameSolver(headless=True)

# Increase timeout for Zip to 60 seconds
zip_solution = solver.solve_zip(timeout_seconds=60)
```

## How It Works

The package uses Selenium with the selenium-wire extension to:

1. Navigate to the LinkedIn game page
2. Wait for the game to load
3. Click the start button
4. Intercept network requests containing game solutions
5. Extract and format the solution data
6. Save the results to a JSON file

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/sebtheo/linkedin-games-scraper.git
cd linkedin-games-scraper

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Using the Makefile

The project includes a Makefile with common development tasks:

```bash
# Install development dependencies
make dev-install

# Run linting
make lint

# Format code
make format

# Run tests
make test

# Build package
make build

# Clean build artifacts
make clean

# Run the package
make run
```

### Local Testing

To run the package locally without installing:

```bash
# Run directly
python run.py

# Or use the module
python -m linkedin_games_scraper
```

## Troubleshooting

- **Browser crashes or fails to start**: Ensure you have the latest version of Chrome and ChromeDriver installed.
- **No solutions found**: LinkedIn may have changed their API. Please check for updates to this package.
- **Slow performance**: Try setting `headless=False` to see what's happening in the browser.

## Licence

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
