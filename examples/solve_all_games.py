#!/usr/bin/env python3
"""Example script that solves all LinkedIn games and prints the solutions."""

import json

from linkedin_games_scraper import GameSolver


def main():
    """Solve all LinkedIn games and print the solutions."""
    print("LinkedIn Games Solver Example")
    print("----------------------------")

    # Create a solver instance
    solver = GameSolver(headless=True)

    try:
        # Solve all games
        print("Solving all LinkedIn games...")
        solver.solve_all_games()

        # Print results
        print("\nResults:")
        print(json.dumps(solver.results, indent=2))

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
