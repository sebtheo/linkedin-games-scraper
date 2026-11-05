"""Fixture tests for Zip, Queens, and Tango payload extraction."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium.webdriver.common.by import By

from linkedin_games_scraper.solver import (
    GameSolver,
    extract_queens_fields,
    extract_tango_solution,
    extract_zip_fields,
)

FIXTURES = Path(__file__).parent / "fixtures"
VOYAGER_URL = (
    "https://www.linkedin.com/voyager/api/graphql?includeWebMetadata=true&variables=(gameTypeId:1)&queryId=voyagerIdentityDashGames.abc"
)
VOYAGER_PAGES_URL = (
    "https://www.linkedin.com/voyager/api/graphql?includeWebMetadata=true"
    "&variables=(gameTypeId:1)&queryId=voyagerIdentityDashGamesPages.abc"
)


class FakeResponse:
    """Minimal selenium-wire response."""

    def __init__(self, body):
        self.body = body.encode("utf-8") if isinstance(body, str) else body
        self.status_code = 200


class FakeRequest:
    """Minimal selenium-wire request."""

    def __init__(self, url, body):
        self.url = url
        self.response = FakeResponse(body)


class FakeSwitch:
    """Records frame switches."""

    def __init__(self):
        self.frames = []

    def frame(self, iframe):
        self.frames.append(iframe)

    def default_content(self):
        self.frames.append("top")


class FakeStartLink:
    """Anchor that the new game shell uses instead of the legacy start button."""

    def __init__(self):
        self.text = "Start game"
        self.clicked = False

    def click(self):
        self.clicked = True


class FakeDriver:
    """Top-document game page with no games iframe."""

    def __init__(self, start_link):
        self.requests = []
        self.switch_to = FakeSwitch()
        self.start_link = start_link
        self.current_url = "https://www.linkedin.com/games/zip"

    def get(self, url):
        self.current_url = url

    def execute_script(self, _script):
        return "complete"

    def find_elements(self, by, value):
        if by == By.CSS_SELECTOR and value == "iframe[title='games']":
            return []
        if by == By.TAG_NAME and value == "iframe":
            return []
        if by == By.ID and value == "launch-footer-start-button":
            return []
        if by == By.CSS_SELECTOR and value == "a, button":
            return [self.start_link]
        return []

    def quit(self):
        return None


class TestPuzzleExtractors(unittest.TestCase):
    """Extractors keep the saved result shapes for both payload styles."""

    def test_zip_flagship_payload_matches_saved_shape(self):
        fields = extract_zip_fields((FIXTURES / "zip_flagship.txt").read_text())
        self.assertEqual(fields["grid"], 7)
        self.assertEqual(fields["sequence"][:3], [0, 27, 33])
        self.assertEqual(len(fields["solution"]), 49)
        self.assertTrue(all(isinstance(cell, int) for cell in fields["solution"]))
        self.assertEqual(fields["solution"][:3], [0, 1, 2])

    def test_zip_voyager_payload_still_extracts(self):
        payload = {"included": [{"gamePuzzle": {"trailGamePuzzle": {"solution": [4, 5, 6], "orderedSequence": [4, 6], "gridSize": 3}}}]}
        fields = extract_zip_fields(payload)
        self.assertEqual(fields["solution"], [4, 5, 6])
        self.assertEqual(fields["sequence"], [4, 6])
        self.assertEqual(fields["grid"], 3)

    def test_queens_flagship_payload_matches_saved_shape(self):
        fields = extract_queens_fields((FIXTURES / "queens_flagship.txt").read_text())
        self.assertEqual(fields["grid"], 9)
        self.assertEqual(fields["solution"][0], (0, 4))
        self.assertEqual(len(fields["solution"]), 9)
        self.assertEqual(len(fields["board"]), 9)
        self.assertEqual(len(fields["board"][0]), 9)
        saved = json.loads(json.dumps({"queens": fields["solution"], "queens_board": fields["board"], "queens_grid": fields["grid"]}))
        self.assertEqual(saved["queens"][0], [0, 4])
        self.assertIsInstance(saved["queens_board"][0][0], int)

    def test_tango_flagship_and_legacy_tokens(self):
        solution = extract_tango_solution((FIXTURES / "tango_flagship.txt").read_text())
        self.assertEqual(len(solution), 36)
        self.assertEqual(solution[:6], "001101")
        self.assertTrue(set(solution) <= {"0", "1"})
        legacy = extract_tango_solution(
            {"included": [{"gamePuzzle": {"lotkaGamePuzzle": {"solution": ["ONE", "ZERO", "LotkaCellValue_ONE", "LotkaCellValue_ZERO"]}}}]}
        )
        self.assertEqual(legacy, "1010")


class TestResponseSelection(unittest.TestCase):
    """The request filter accepts Voyager games and the flagship puzzle document."""

    def setUp(self):
        self._results = tempfile.TemporaryDirectory()
        self.results_dir = self._results.name

    def tearDown(self):
        self._results.cleanup()

    @patch("linkedin_games_scraper.solver.webdriver")
    def test_voyager_game_response_is_selected(self, mock_webdriver):
        driver = FakeDriver(FakeStartLink())
        mock_webdriver.Chrome.return_value = driver
        solver = GameSolver(headless=True, results_dir=self.results_dir)
        body = (FIXTURES / "pinpoint_voyager.json").read_text()
        driver.requests = [
            FakeRequest(VOYAGER_PAGES_URL, body),
            FakeRequest(VOYAGER_URL, body),
        ]
        self.assertEqual(solver._find_pinpoint_solution(), "Terms that come after stone")

    @patch("linkedin_games_scraper.solver.webdriver")
    def test_flagship_zip_response_is_selected(self, mock_webdriver):
        driver = FakeDriver(FakeStartLink())
        mock_webdriver.Chrome.return_value = driver
        solver = GameSolver(headless=True, results_dir=self.results_dir)
        fragment = (FIXTURES / "zip_flagship.txt").read_text()
        driver.requests = [FakeRequest("https://www.linkedin.com/flagship-web/games/zip/?skipStartScreen=true", fragment)]
        sequence = solver._find_zip_solution()
        self.assertEqual(sequence[:3], [0, 27, 33])
        self.assertEqual(len(solver.results["data"]["zip"]), 49)
        self.assertEqual(solver.results["data"]["zip_grid"], 7)

    @patch("linkedin_games_scraper.solver.time.sleep", return_value=None)
    @patch("linkedin_games_scraper.solver.webdriver")
    def test_missing_iframe_still_scans_requests(self, mock_webdriver, _sleep):
        start_link = FakeStartLink()
        driver = FakeDriver(start_link)
        mock_webdriver.Chrome.return_value = driver
        solver = GameSolver(headless=True, results_dir=self.results_dir)

        started = solver._start_game("https://www.linkedin.com/games/zip", navigation_timeout=1)
        self.assertTrue(started)
        self.assertTrue(start_link.clicked)
        self.assertNotIn("iframe", driver.switch_to.frames)

        fragment = (FIXTURES / "zip_flagship.txt").read_text()
        driver.requests = [FakeRequest("https://www.linkedin.com/flagship-web/games/zip/?skipStartScreen=true", fragment)]
        self.assertEqual(solver._find_zip_solution()[:3], [0, 27, 33])
