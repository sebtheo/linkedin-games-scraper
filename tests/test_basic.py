"""Basic tests for the LinkedIn Games Scraper package."""

import unittest
from unittest.mock import MagicMock, patch

from linkedin_games_scraper import GameSolver


class TestGameSolver(unittest.TestCase):
    """Basic tests for the GameSolver class."""

    @patch("linkedin_games_scraper.solver.webdriver")
    def test_init(self, mock_webdriver):
        """Test that the GameSolver initializes properly."""
        mock_driver = MagicMock()
        mock_webdriver.Chrome.return_value = mock_driver

        solver = GameSolver(headless=True)

        # Check that the driver was initialized
        self.assertIsNotNone(solver.driver)

        # Check that the results dictionary was initialized
        self.assertEqual(solver.results, {"data": {}})

    @patch("linkedin_games_scraper.solver.webdriver")
    def test_custom_results_dir(self, mock_webdriver):
        """Test that custom results directory is set properly."""
        mock_driver = MagicMock()
        mock_webdriver.Chrome.return_value = mock_driver

        custom_dir = "custom_results"
        solver = GameSolver(headless=True, results_dir=custom_dir)

        # Check that the custom results directory was set
        self.assertEqual(solver.results_dir, custom_dir)

    @patch("linkedin_games_scraper.solver.webdriver")
    def test_game_urls(self, mock_webdriver):
        """Test that game URLs are defined correctly."""
        mock_driver = MagicMock()
        mock_webdriver.Chrome.return_value = mock_driver

        solver = GameSolver(headless=True)

        # Check that game URLs are defined
        self.assertIn("pinpoint", solver.GAME_URLS)
        self.assertIn("crossclimb", solver.GAME_URLS)
        self.assertIn("zip", solver.GAME_URLS)
        self.assertIn("queens", solver.GAME_URLS)
        self.assertIn("tango", solver.GAME_URLS)
        self.assertIn("mini_sudoku", solver.GAME_URLS)

        # Check that game type IDs are defined
        self.assertIn("pinpoint", solver.GAME_TYPE_IDS)
        self.assertIn("crossclimb", solver.GAME_TYPE_IDS)
        self.assertIn("zip", solver.GAME_TYPE_IDS)
        self.assertIn("queens", solver.GAME_TYPE_IDS)
        self.assertIn("tango", solver.GAME_TYPE_IDS)
        self.assertIn("mini_sudoku", solver.GAME_TYPE_IDS)


if __name__ == "__main__":
    unittest.main()
