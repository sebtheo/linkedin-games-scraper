"""Solver module."""

import json
import logging
import os
import re
import time
from datetime import datetime

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
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
console_handler.setFormatter(logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(console_handler)

_INTERESTING_URL_MARKERS = ("graphql", "voyager", "sdui", "game", "puzzle")
_URN_RE = re.compile(r"urn:li:[A-Za-z0-9_()+.,:%-]+", re.IGNORECASE)
_MEMBER_RE = re.compile(r"ACo[A-Za-z0-9_-]{10,}")
_SECRET_QUERY_RE = re.compile(r"((?:csrf|token|cookie|li_at|session)[=:])[^&\s\"']+", re.IGNORECASE)


def redact_text(value):
    """Remove member URNs, account ids, and token-like query values."""
    if not isinstance(value, str):
        return value
    redacted = _URN_RE.sub("urn:li:redacted", value)
    redacted = _MEMBER_RE.sub("member-redacted", redacted)
    return _SECRET_QUERY_RE.sub(r"\1redacted", redacted)


def json_skeleton(value, depth=0):
    """Keep object keys and collection sizes, dropping payload values."""
    if depth > 12:
        return "..."
    if isinstance(value, dict):
        return {str(key): json_skeleton(item, depth + 1) for key, item in value.items()}
    if isinstance(value, list):
        item = json_skeleton(value[0], depth + 1) if value else None
        return {"len": len(value), "item": item}
    if isinstance(value, str):
        redacted = redact_text(value)
        return {"type": "str", "len": len(redacted)}
    if value is None or isinstance(value, (bool, int, float)):
        return {"type": type(value).__name__}
    return {"type": type(value).__name__}


def extract_json_object_after_key(text, key):
    """Return the JSON object that follows a quoted key in a flight payload."""
    needle = f'"{key}":'
    start = 0
    while True:
        index = text.find(needle, start)
        if index < 0:
            return None
        brace = text.find("{", index + len(needle))
        if brace < 0:
            return None
        parsed = _parse_json_object_at(text, brace)
        if isinstance(parsed, dict) and "solution" in parsed:
            return parsed
        start = index + len(needle)


def _parse_json_object_at(text, brace):
    """Parse one JSON object beginning at an opening brace."""
    depth = 0
    in_string = False
    escaped = False
    for index in range(brace, len(text)):
        character = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[brace : index + 1])
                except json.JSONDecodeError:
                    return None
    return None


def find_named_puzzle(data, key):
    """Find a puzzle object in GraphQL JSON or an embedded flagship payload."""
    if isinstance(data, str):
        return extract_json_object_after_key(data, key)
    if isinstance(data, dict):
        puzzle = data.get(key)
        if isinstance(puzzle, dict) and "solution" in puzzle:
            return puzzle
        for value in data.values():
            found = find_named_puzzle(value, key)
            if found:
                return found
    elif isinstance(data, list):
        for item in data:
            found = find_named_puzzle(item, key)
            if found:
                return found
    return None


def extract_zip_fields(data):
    """Return the Zip path, numbered sequence, and grid size."""
    puzzle = find_named_puzzle(data, "trailGamePuzzle")
    if not puzzle or "solution" not in puzzle or "orderedSequence" not in puzzle:
        return None
    return {
        "solution": puzzle["solution"],
        "sequence": puzzle["orderedSequence"],
        "grid": puzzle.get("gridSize"),
    }


def extract_queens_fields(data):
    """Return Queens coordinates, colour rows, and grid size."""
    puzzle = find_named_puzzle(data, "queensGamePuzzle")
    if not puzzle or "solution" not in puzzle:
        return None
    solution = [(queen["row"], queen["col"]) for queen in puzzle["solution"]]
    board = [row["colors"] for row in puzzle.get("colorGrid", [])]
    return {"solution": solution, "board": board, "grid": puzzle.get("gridSize")}


def _tango_bit(item):
    """Map a Tango cell token to 1 or 0."""
    text = str(item)
    if text == "ONE" or text.endswith("_ONE"):
        return "1"
    return "0"


def extract_tango_solution(data):
    """Return the Tango grid as a string of 0 and 1."""
    puzzle = find_named_puzzle(data, "lotkaGamePuzzle")
    if not puzzle or "solution" not in puzzle:
        return None
    return "".join(_tango_bit(item) for item in puzzle["solution"])


class GameSolver:
    """GameSolver class."""

    # Game URLs
    GAME_URLS = {
        "pinpoint": "https://www.linkedin.com/games/pinpoint",
        "crossclimb": "https://www.linkedin.com/games/crossclimb",
        "zip": "https://www.linkedin.com/games/zip",
        "queens": "https://www.linkedin.com/games/queens",
        "tango": "https://www.linkedin.com/games/tango",
        "mini_sudoku": "https://www.linkedin.com/games/mini-sudoku",
    }

    # Game type IDs
    GAME_TYPE_IDS = {
        "pinpoint": 1,
        "crossclimb": 2,
        "queens": 3,
        "tango": 5,
        "zip": 6,
        "mini_sudoku": 7,
    }

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
        self.driver = webdriver.Chrome(seleniumwire_options=self.seleniumwire_options, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)

        # Initialise results dictionary
        self.results = {"data": {}}

        # Create results directory if it doesn't exist
        self.results_dir = results_dir or "results"
        os.makedirs(self.results_dir, exist_ok=True)

    def _request_body(self, request):
        """Decode a response body, or return an empty string."""
        body = getattr(request.response, "body", b"") or b""
        if isinstance(body, bytes):
            return body.decode("utf-8", errors="replace")
        return str(body)

    def _is_voyager_game_url(self, url, game_type_id):
        """Return whether a URL is the Voyager daily-game query."""
        return (
            "voyager/api/graphql" in url
            and f"gameTypeId:{game_type_id}" in url
            and "voyagerIdentityDashGames" in url
            and "voyagerIdentityDashGamesPages" not in url
        )

    def _find_game_response(self, game_type_id, puzzle_key=None):
        """Find a Voyager game response or a flagship payload that contains the puzzle."""
        saw_request = False
        for request in self.driver.requests:
            saw_request = True
            if not request.response:
                continue

            url = request.url or ""
            body = self._request_body(request)
            url_match = self._is_voyager_game_url(url, game_type_id)
            if not body or (not url_match and not (puzzle_key and puzzle_key in body)):
                continue

            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = body

            if puzzle_key and not find_named_puzzle(parsed, puzzle_key):
                continue

            logger.info(f"Found candidate response for gameTypeId {game_type_id}: {redact_text(url)}")
            return parsed

        if not saw_request:
            logger.info("No network requests captured yet")
        return None

    def _log_unmatched_game_urls(self, game_label):
        """Log distinct game-related URLs once when no puzzle response matched."""
        urls = []
        for request in self.driver.requests:
            url = request.url or ""
            lowered = url.lower()
            if any(marker in lowered for marker in ("graphql", "voyager", "sdui", "flagship-web/games", "puzzle")):
                urls.append(redact_text(url))
        unique_urls = sorted(set(urls))
        logger.info(f"No {game_label} puzzle response. Game-related URLs: {unique_urls}")

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
        """Find the solution in the Zip game payload."""
        data = self._find_game_response(self.GAME_TYPE_IDS["zip"], puzzle_key="trailGamePuzzle")
        if not data:
            return None
        try:
            fields = extract_zip_fields(data)
            if not fields:
                logger.error("Zip payload did not contain a trail puzzle")
                return None
            logger.info("Zip solution sequence:")
            logger.info(f"Order: {fields['sequence']}")
            self.results["data"]["zip"] = fields["solution"]
            self.results["data"]["zip_sequence"] = fields["sequence"]
            self.results["data"]["zip_grid"] = fields["grid"]
            return fields["sequence"]
        except Exception as error:
            logger.error(f"Error extracting Zip solution: {error}")
        return None

    def _find_queens_solution(self):
        """Find the solution in the Queens game payload."""
        data = self._find_game_response(self.GAME_TYPE_IDS["queens"], puzzle_key="queensGamePuzzle")
        if not data:
            return None
        try:
            fields = extract_queens_fields(data)
            if not fields:
                logger.error("Queens payload did not contain a queens puzzle")
                return None
            logger.info("Queens solution coordinates:")
            for row, col in fields["solution"]:
                logger.info(f"Queen at row {row}, column {col}")
            for colors in fields["board"]:
                logger.info(f"Row: {colors}")
            self.results["data"]["queens"] = fields["solution"]
            self.results["data"]["queens_board"] = fields["board"]
            self.results["data"]["queens_grid"] = fields["grid"]
            return fields["solution"]
        except Exception as error:
            logger.error(f"Error extracting Queens solution: {error}")
        return None

    def _find_tango_solution(self):
        """Find the solution in the Tango game payload."""
        data = self._find_game_response(self.GAME_TYPE_IDS["tango"], puzzle_key="lotkaGamePuzzle")
        if not data:
            return None
        try:
            solution = extract_tango_solution(data)
            if not solution:
                logger.error("Tango payload did not contain a lotka puzzle")
                return None
            logger.info(f"Tango solution: {solution}")
            self.results["data"]["tango"] = solution
            return solution
        except Exception as error:
            logger.error(f"Error extracting Tango solution: {error}")
        return None

    def _find_mini_sudoku_solution(self):
        """Find the solution in the Mini Sudoku GraphQL response."""
        logger.info("Starting Mini Sudoku solution extraction...")
        data = self._find_game_response(self.GAME_TYPE_IDS["mini_sudoku"])
        if data:
            logger.info("Found Mini Sudoku data, extracting solution...")
            try:
                mini_sudoku_puzzle = None
                if "included" in data and data["included"]:
                    for item in data["included"]:
                        game_puzzle = item.get("gamePuzzle")
                        if game_puzzle and game_puzzle.get("miniSudokuGamePuzzle"):
                            mini_sudoku_puzzle = game_puzzle["miniSudokuGamePuzzle"]
                            logger.info("Found Mini Sudoku puzzle in included item")
                            break

                    if not mini_sudoku_puzzle:
                        logger.error("No Mini Sudoku puzzle found in included array")
                        for i, item in enumerate(data["included"]):
                            logger.error(f"Included item {i} keys: {list(item.keys())}")
                            if "gamePuzzle" in item:
                                game_puzzle = item["gamePuzzle"]
                                logger.error(
                                    f"GamePuzzle types in item {i}: {[k for k in game_puzzle.keys() if game_puzzle[k] is not None]}"
                                )
                        return None
                else:
                    logger.error("No 'included' array found in response")
                    logger.error(f"Available keys: {list(data.keys())}")
                    return None

                solution = mini_sudoku_puzzle["solution"]
                grid_size = mini_sudoku_puzzle.get("gridRowSize", 6)
                preset_cells = mini_sudoku_puzzle.get("presetCellIdxes", [])
                title = mini_sudoku_puzzle.get("name", "Unknown")

                logger.info(f"Mini Sudoku solution for '{title}':")
                logger.info(f"Grid size: {grid_size}x{grid_size}")
                logger.info(f"Preset cells: {preset_cells}")
                logger.info(f"Solution: {solution}")

                for i in range(grid_size):
                    start_idx = i * grid_size
                    end_idx = start_idx + grid_size
                    row = solution[start_idx:end_idx]
                    logger.info(f"Row {i + 1}: {row}")

                self.results["data"]["mini_sudoku"] = {
                    "solution": solution,
                    "grid_size": grid_size,
                    "preset_cells": preset_cells,
                    "title": title,
                }
                return solution
            except Exception as e:
                logger.error(f"Error extracting Mini Sudoku solution: {str(e)}")
                logger.error(f"Response structure: {data.keys() if isinstance(data, dict) else 'Not a dict'}")
        else:
            logger.error("No Mini Sudoku data found")
        return None

    def _start_game(self, game_url, navigation_timeout=30):
        """Start a game and find its solution."""
        # Clear existing requests
        del self.driver.requests

        # Navigate to game
        logger.info(f"Navigating to game URL: {game_url}")
        self.driver.get(game_url)

        # Wait for the page to load completely with a timeout
        start_time = time.time()
        timeout = navigation_timeout

        while time.time() - start_time < timeout:
            try:
                WebDriverWait(self.driver, 5).until(lambda d: d.execute_script("return document.readyState") == "complete")
                logger.info("Page loaded successfully")
                break
            except Exception as e:
                if time.time() - start_time >= timeout:
                    logger.error(f"Page load timed out after {timeout} seconds")
                    return None
                else:
                    logger.info(f"Waiting for page load... ({str(e)})")
                time.sleep(1)
                continue

        # The games iframe is optional. Zip, Queens, and Tango render in the top document.
        self._open_game_surface()
        self._click_start_control()

        # Wait for game data to load
        logger.info("Waiting briefly for network requests to populate...")
        time.sleep(3)
        return True

    def _open_game_surface(self):
        """Switch into the games iframe when it exists, otherwise stay on the top document."""
        deadline = time.time() + 8
        while time.time() < deadline:
            self.driver.switch_to.default_content()
            games_frames = self.driver.find_elements(By.CSS_SELECTOR, "iframe[title='games']")
            if games_frames:
                self.driver.switch_to.frame(games_frames[0])
                logger.info("Successfully switched to iframe")
                return "iframe"

            for iframe in self.driver.find_elements(By.TAG_NAME, "iframe"):
                src = (iframe.get_attribute("src") or "").lower()
                if "linkedin.com" in src and "game" in src:
                    self.driver.switch_to.frame(iframe)
                    logger.info("Switched to LinkedIn game iframe")
                    return "game-iframe"

            if self._start_control_in_current_document():
                logger.info("Games iframe not present; using the top document")
                return "top"
            time.sleep(0.25)

        self.driver.switch_to.default_content()
        logger.info("Games iframe not present; staying on the top document")
        return "top"

    def _start_control_in_current_document(self):
        """Return whether the current document has a start button or Start game link."""
        if self.driver.find_elements(By.ID, "launch-footer-start-button"):
            return True
        for element in self.driver.find_elements(By.CSS_SELECTOR, "a, button"):
            if "start game" in (element.text or "").strip().lower():
                return True
        return False

    def _click_start_control(self):
        """Click the legacy start button or the Start game link. Missing controls are not fatal."""
        for context in ("current", "top"):
            try:
                if context == "top":
                    self.driver.switch_to.default_content()
                buttons = self.driver.find_elements(By.ID, "launch-footer-start-button")
                if buttons:
                    buttons[0].click()
                    logger.info("Successfully clicked start button")
                    return "launch-footer-start-button"
                for element in self.driver.find_elements(By.CSS_SELECTOR, "a, button"):
                    if "start game" in (element.text or "").strip().lower():
                        element.click()
                        logger.info("Successfully clicked Start game link")
                        return "start-game"
            except Exception as error:
                logger.info(f"Could not click start control in {context}: {error}")
        logger.info("Start control not present")
        return None

    def _iframe_snapshot(self):
        """Describe iframes and the start button without failing the capture."""
        self.driver.switch_to.default_content()
        frames = []
        for iframe in self.driver.find_elements(By.TAG_NAME, "iframe"):
            frames.append(
                {
                    "title": iframe.get_attribute("title") or "",
                    "id": iframe.get_attribute("id") or "",
                    "src": redact_text(iframe.get_attribute("src") or ""),
                }
            )
        return {
            "url": redact_text(self.driver.current_url),
            "iframes": frames,
            "start_button_in_top": self._start_control_in_current_document(),
        }

    def _click_start_if_present(self):
        """Click the launch button or Start game link without failing the capture."""
        self.driver.switch_to.default_content()
        return self._click_start_control()

    def _redacted_game_requests(self):
        """Return URL, status, and a key skeleton for game-related responses."""
        records = []
        seen = set()
        for request in self.driver.requests:
            if not request.response:
                continue
            url = request.url or ""
            lowered = url.lower()
            if not any(marker in lowered for marker in _INTERESTING_URL_MARKERS):
                continue
            redacted_url = redact_text(url.split("?", 1)[0] if "csrf" in lowered or "token" in lowered else url)
            try:
                body = request.response.body.decode("utf-8", errors="replace")
            except Exception:
                body = ""
            parsed = None
            skeleton = None
            if body:
                try:
                    parsed = json.loads(body)
                    skeleton = json_skeleton(parsed)
                except Exception:
                    skeleton = {"type": "non-json", "len": len(body)}
            signature = (redacted_url, request.response.status_code, json.dumps(skeleton, sort_keys=True) if skeleton else "")
            if signature in seen:
                continue
            seen.add(signature)
            records.append(
                {
                    "url": redacted_url,
                    "status": request.response.status_code,
                    "skeleton": skeleton,
                    "body_markers": sorted(
                        marker
                        for marker in (
                            "trailGamePuzzle",
                            "queensGamePuzzle",
                            "lotkaGamePuzzle",
                            "miniSudokuGamePuzzle",
                            "blueprintGamePuzzle",
                            "crossClimbGamePuzzle",
                            "orderedSequence",
                            "colorGrid",
                            "updateGameState",
                            "gameTypeId",
                            "sdui",
                        )
                        if marker in body
                    ),
                }
            )
        return records

    def capture_game_traffic(self, games=("zip", "queens", "tango"), wait_seconds=8):
        """Visit games anonymously and record redacted DOM and request shapes."""
        captures = []
        for game in games:
            del self.driver.requests
            game_url = self.GAME_URLS[game]
            logger.info(f"Capturing {game}: {game_url}")
            self.driver.get(game_url)
            try:
                WebDriverWait(self.driver, 20).until(lambda d: d.execute_script("return document.readyState") == "complete")
            except Exception as error:
                logger.info(f"Page ready wait ended: {error}")
            time.sleep(3)
            before = self._iframe_snapshot()
            clicked = self._click_start_if_present()
            time.sleep(wait_seconds)
            after = self._iframe_snapshot()
            captures.append(
                {
                    "game": game,
                    "requested_url": game_url,
                    "clicked_start_in": clicked,
                    "before_start": before,
                    "after_start": after,
                    "requests": self._redacted_game_requests(),
                }
            )
            self.driver.switch_to.default_content()
        return captures

    def _poll_for_solution(self, game_label, finder, timeout_seconds):
        """Poll for a solution and stop once startup produced no puzzle response."""
        deadline = time.time() + timeout_seconds
        empty_scans = 0
        solution = None
        while time.time() < deadline and not solution:
            solution = finder()
            if solution:
                break
            empty_scans += 1
            if empty_scans >= 8:
                break
            logger.info(f"Waiting for {game_label} solution...")
            time.sleep(1)

        if solution:
            logger.info(f"SUCCESS - {game_label} solution found!")
        else:
            self._log_unmatched_game_urls(game_label)
            logger.warning(f"ERROR - No {game_label} solution found (timeout)")
        return solution

    def solve_pinpoint(self, timeout_seconds: int = 30):
        """Solve the Pinpoint game."""
        logger.info("Solving Pinpoint...")
        self._start_game(self.GAME_URLS["pinpoint"], navigation_timeout=timeout_seconds)
        return self._poll_for_solution("Pinpoint", self._find_pinpoint_solution, timeout_seconds)

    def solve_crossclimb(self, timeout_seconds: int = 30):
        """Solve the CrossClimb game."""
        logger.info("Solving CrossClimb...")
        self._start_game(self.GAME_URLS["crossclimb"], navigation_timeout=timeout_seconds)
        return self._poll_for_solution("CrossClimb", self._find_crossclimb_solution, timeout_seconds)

    def solve_zip(self, timeout_seconds: int = 30):
        """Solve the Zip game."""
        logger.info("Solving Zip...")
        self._start_game(self.GAME_URLS["zip"], navigation_timeout=timeout_seconds)
        return self._poll_for_solution("Zip", self._find_zip_solution, timeout_seconds)

    def solve_queens(self, timeout_seconds: int = 30):
        """Solve the Queens game."""
        logger.info("Solving Queens...")
        self._start_game(self.GAME_URLS["queens"], navigation_timeout=timeout_seconds)
        return self._poll_for_solution("Queens", self._find_queens_solution, timeout_seconds)

    def solve_tango(self, timeout_seconds: int = 30):
        """Solve the Tango game."""
        logger.info("Solving Tango...")
        self._start_game(self.GAME_URLS["tango"], navigation_timeout=timeout_seconds)
        return self._poll_for_solution("Tango", self._find_tango_solution, timeout_seconds)

    def solve_mini_sudoku(self, timeout_seconds: int = 30):
        """Solve the Mini Sudoku game."""
        logger.info("Solving Mini Sudoku...")
        self._start_game(self.GAME_URLS["mini_sudoku"], navigation_timeout=timeout_seconds)
        return self._poll_for_solution("Mini Sudoku", self._find_mini_sudoku_solution, timeout_seconds)

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

            # Solve Mini Sudoku
            mini_sudoku_solution = self.solve_mini_sudoku()
            if mini_sudoku_solution:
                results["mini_sudoku"] = mini_sudoku_solution

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
