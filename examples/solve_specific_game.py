#!/usr/bin/env python3
"""Example script that solves a specific LinkedIn game."""

from linkedin_games_scraper import GameSolver


def main():
    """Solve a specific LinkedIn game."""
    print("LinkedIn Specific Game Solver Example")
    print("------------------------------------")

    # Create a solver instance
    solver = GameSolver(headless=True)

    try:
        # Solve Pinpoint game
        print("Solving Pinpoint game...")
        pinpoint_solution = solver.solve_pinpoint()

        if pinpoint_solution:
            print(f"Pinpoint solution found: {pinpoint_solution}")
        else:
            print("No Pinpoint solution found.")

        # Save results
        results_file = solver.cleanup()
        print(f"Results saved to {results_file}")

    except Exception as e:
        print(f"Error: {str(e)}")
        # Make sure to clean up even if there's an error
        solver.cleanup()


if __name__ == "__main__":
    main()
