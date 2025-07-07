#!/usr/bin/env python3
"""Simple script to run the LinkedIn Games Scraper package."""

from linkedin_games_scraper import GameSolver

if __name__ == "__main__":
    print("LinkedIn Games Solver")
    print("--------------------")

    # Create a solver instance
    solver = GameSolver(headless=True)

    try:
        # Solve all games
        print("Solving all LinkedIn games...")
        results = solver.solve_all_games()

        print("\nResults:")
        for game, solution in results.items():
            print(f"{game}: {solution}")

    except Exception as e:
        print(f"Error: {str(e)}")
        # Make sure to clean up even if there's an error
        solver.cleanup()
