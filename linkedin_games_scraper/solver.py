"""Solver module."""
import json
import logging
import os
import time
from datetime import datetime

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from seleniumwire import webdriver

# Set up logging
# First, disable all loggers
for name in logging.Logger.manager.loggerDict.keys():
    logging.getLogger(name).disabled = True

# Then set up our logger
logger = logging.getLogger(__name__)
logger.disabled = False
logger.setLevel(logging.INFO)

# Create console handler with formatting
console_handler = logging.StreamHandler()
console_handler.setFormatter(
    logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
)
logger.addHandler(console_handler)


class GameSolver:
    """GameSolver class."""

    # Game URLs
    GAME_URLS = {
        "pinpoint": "https://www.linkedin.com/games/pinpoint",
        "crossclimb": "https://www.linkedin.com/games/crossclimb",
        "zip": "https://www.linkedin.com/games/zip",
        "queens": "https://www.linkedin.com/games/queens",
        "tango": "https://www.linkedin.com/games/tango",
    }

    # Game type IDs
    GAME_TYPE_IDS = {"pinpoint": 1, "crossclimb": 2, "queens": 3, "tango": 5, "zip": 6}

    def __init__(self, headless=True, results_dir=None):
        """Initialise the GameSolver."""
        # Configure Selenium-wire to capture all requests
        self.seleniumwire_options = {"disable_encoding": True, "verify_ssl": False}

        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"--user-data-dir=/tmp/chrome-data-{time.time()}")

        # Initialise the driver
        self.driver = webdriver.Chrome(
            seleniumwire_options=self.seleniumwire_options, options=chrome_options
        )
        self.wait = WebDriverWait(self.driver, 10)

        # Initialise results dictionary
        self.results = {"data": {}}

        # Create results directory if it doesn't exist
        self.results_dir = results_dir or "results"
        os.makedirs(self.results_dir, exist_ok=True)

    def _find_game_response(self, game_type_id):
        """Find game response in requests."""
        for request in self.driver.requests:
            if not request.response:
                continue

            url = request.url
            if (
                "voyager/api/graphql" in url
                and f"gameTypeId:{game_type_id}" in url
                and "voyagerIdentityDashGames" in url
                and "voyagerIdentityDashGamesPages" not in url
            ):
                try:
                    body = request.response.body.decode("utf-8")
                    return json.loads(body)
                except Exception as e:
                    logger.error(f"Error parsing response: {str(e)}")
        return None

    def _find_pinpoint_solution(self):
        """Find the solution in the Pinpoint GraphQL response."""
        data = self._find_game_response(self.GAME_TYPE_IDS["pinpoint"])
        if data:
            try:
                solution = data["included"][0]["gamePuzzle"]["blueprintGamePuzzle"]["solutions"][0]
                logger.info(f"Pinpoint solution: {solution}")
                self.results["data"]["pinpoint"] = solution
                return solution
            except Exception as e:
                logger.error(f"Error extracting Pinpoint solution: {str(e)}")
        return None

    def _find_crossclimb_solution(self):
        """Find the solution in the CrossClimb GraphQL response."""
        data = self._find_game_response(self.GAME_TYPE_IDS["crossclimb"])
        if data:
            try:
                rungs = data["included"][0]["gamePuzzle"]["crossClimbGamePuzzle"]["rungs"]

                # Sort rungs by solutionRungIndex and format solution
                sorted_rungs = sorted(rungs, key=lambda x: x["solutionRungIndex"])
                solution = [(rung["solutionRungIndex"], rung["word"]) for rung in sorted_rungs]

                logger.info("CrossClimb solution:")
                for index, word in solution:
                    logger.info(f"Position {index}: {word}")

                self.results["data"]["crossclimb"] = solution
                return solution
            except Exception as e:
                logger.error(f"Error extracting CrossClimb solution: {str(e)}")
        return None

    def _find_zip_solution(self):
        """Find the solution in the Zip GraphQL response."""
        data = self._find_game_response(self.GAME_TYPE_IDS["zip"])
        if data:
            try:
                sequence = data["included"][0]["gamePuzzle"]["trailGamePuzzle"]["orderedSequence"]
                solution = data["included"][0]["gamePuzzle"]["trailGamePuzzle"]["solution"]
                grid = data["included"][0]["gamePuzzle"]["trailGamePuzzle"]["gridSize"]

                logger.info("Zip solution sequence:")
                logger.info(f"Order: {sequence}")

                self.results["data"]["zip"] = solution
                self.results["data"]["zip_sequence"] = sequence
                self.results["data"]["zip_grid"] = grid

                return sequence
            except Exception as e:
                logger.error(f"Error extracting Zip solution: {str(e)}")
        return None

    def _find_queens_solution(self):
        """Find the solution in the Queens GraphQL response."""
        data = self._find_game_response(self.GAME_TYPE_IDS["queens"])
        if data:
            try:
                queens = data["included"][0]["gamePuzzle"]["queensGamePuzzle"]["solution"]
                board = data["included"][0]["gamePuzzle"]["queensGamePuzzle"]["colorGrid"]
                grid = data["included"][0]["gamePuzzle"]["queensGamePuzzle"]["gridSize"]

                logger.info("Queens solution coordinates:")
                solution = []
                for queen in queens:
                    row, col = queen["row"], queen["col"]
                    solution.append((row, col))
                    logger.info(f"Queen at row {row}, column {col}")
                board_setup = []
                for row in board:
                    board_setup.append(row["colors"])
                    logger.info(f"Row: {row['colors']}")

                self.results["data"]["queens"] = solution
                self.results["data"]["queens_board"] = board_setup
                self.results["data"]["queens_grid"] = grid
                return solution
            except Exception as e:
                logger.error(f"Error extracting Queens solution: {str(e)}")
        return None

    def _find_tango_solution(self):
        """Find the solution in the Tango GraphQL response."""
        data = self._find_game_response(self.GAME_TYPE_IDS["tango"])
        if data:
            try:
                solution_array = data["included"][0]["gamePuzzle"]["lotkaGamePuzzle"]["solution"]

                logger.info("Tango solution sequence:")
                solution = ""
                for item in solution_array:
                    if item == "ONE":
                        solution += "1"
                    else:
                        solution += "0"

                logger.info(f"Tango solution: {solution}")

                self.results["data"]["tango"] = solution
                return solution
            except Exception as e:
                logger.error(f"Error extracting Tango solution: {str(e)}")
        return None

    def _start_game(self, game_url):
        """Start a game and find its solution."""
        # Clear existing requests
        del self.driver.requests

        # Navigate to game
        self.driver.get(game_url)

        # Wait for the page to load completely with a 2-minute timeout
        start_time = time.time()
        timeout = 120  # 2 minutes

        while time.time() - start_time < timeout:
            try:
                WebDriverWait(self.driver, 5).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                logger.info("Page loaded successfully")
                break
            except Exception as e:
                if time.time() - start_time >= timeout:
                    logger.error("Page load timed out after 2 minutes")
                    return None
                else:
                    logger.info(f"Error loading page: {str(e)}")
                time.sleep(1)
                continue

        # Wait for and switch to the iframe
        try:
            logger.info("Waiting for iframe to be present")
            iframe = WebDriverWait(self.driver, 10).until(
                expected_conditions.presence_of_element_located(
                    (By.CSS_SELECTOR, "iframe[title='games']")
                )
            )
            logger.info("Found iframe, switching to it")
            self.driver.switch_to.frame(iframe)
            logger.info("Successfully switched to iframe")
        except Exception as e:
            logger.error(f"Failed to switch to iframe: {str(e)}")
            return None

        # Find and click start button
        try:
            logger.info("Looking for start button")
            start_button = WebDriverWait(self.driver, 5).until(
                expected_conditions.element_to_be_clickable((By.ID, "launch-footer-start-button"))
            )
            logger.info("Found start button, clicking")
            start_button.click()
            logger.info("Successfully clicked start button")
        except Exception as e:
            logger.error(f"Failed to click start button: {str(e)}")
            # return None

        # Wait for game data to load
        time.sleep(3)

    def solve_pinpoint(self):
        """Solve the Pinpoint game."""
        logger.info("Solving Pinpoint...")
        self._start_game(self.GAME_URLS["pinpoint"])
        solution = self._find_pinpoint_solution()

        if solution:
            logger.info("SUCCESS - Pinpoint solution found!")
        else:
            logger.warning("ERROR - No Pinpoint solution found")

        return solution

    def solve_crossclimb(self):
        """Solve the CrossClimb game."""
        logger.info("Solving CrossClimb...")
        self._start_game(self.GAME_URLS["crossclimb"])
        solution = self._find_crossclimb_solution()

        if solution:
            logger.info("SUCCESS - CrossClimb solution found!")
        else:
            logger.warning("ERROR - No CrossClimb solution found")

        return solution

    def solve_zip(self):
        """Solve the Zip game."""
        logger.info("Solving Zip...")
        self._start_game(self.GAME_URLS["zip"])
        solution = self._find_zip_solution()

        if solution:
            logger.info("SUCCESS - Zip solution found!")
        else:
            logger.warning("ERROR - No Zip solution found")

        return solution

    def solve_queens(self):
        """Solve the Queens game."""
        logger.info("Solving Queens...")
        self._start_game(self.GAME_URLS["queens"])
        solution = self._find_queens_solution()

        if solution:
            logger.info("SUCCESS - Queens solution found!")
        else:
            logger.warning("ERROR - No Queens solution found")

        return solution

    def solve_tango(self):
        """Solve the Tango game."""
        logger.info("Solving Tango...")
        self._start_game(self.GAME_URLS["tango"])
        solution = self._find_tango_solution()

        if solution:
            logger.info("SUCCESS - Tango solution found!")
        else:
            logger.warning("ERROR - No Tango solution found")

        return solution

    def save_results(self, filename=None):
        """Save results to a JSON file."""
        if not filename:
            filename = f"{self.results_dir}/{datetime.now().strftime('%d-%m-%Y')}.json"
        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Results saved to {filename}")
        return filename

    def cleanup(self):
        """Close the browser and save results."""
        if self.driver:
            self.driver.quit()
        return self.save_results()

    def solve_all_games(self):
        """Solve all LinkedIn games."""
        results = {}

        try:
            # Solve Pinpoint
            pinpoint_solution = self.solve_pinpoint()
            if pinpoint_solution:
                results["pinpoint"] = pinpoint_solution

            # Solve CrossClimb
            crossclimb_solution = self.solve_crossclimb()
            if crossclimb_solution:
                results["crossclimb"] = crossclimb_solution

            # Solve Zip
            zip_solution = self.solve_zip()
            if zip_solution:
                results["zip"] = zip_solution

            # Solve Queens
            queens_solution = self.solve_queens()
            if queens_solution:
                results["queens"] = queens_solution

            # Solve Tango
            tango_solution = self.solve_tango()
            if tango_solution:
                results["tango"] = tango_solution

        finally:
            self.cleanup()

        return results


# Main function
def main():
    """Run the LinkedIn Games Solver."""
    solver = GameSolver(headless=True)

    try:
        # Solve all games
        solver.solve_all_games()
    finally:
        solver.cleanup()


if __name__ == "__main__":
    main()
