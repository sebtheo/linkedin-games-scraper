"""Setup module."""

from setuptools import find_packages, setup

with open("README.md", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="linkedin_games_scraper",
    version="0.2.0",
    author="LinkedIn Games Scraper",
    author_email="seb@theo4.uk",
    description="A package to solve LinkedIn games by extracting solutions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sebtheo/linkedin-games-scraper",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[
        "selenium-wire>=5.1.0",
        "selenium>=4.0.0",
        "blinker==1.7",
        "setuptools>=69.0.3",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "ruff>=0.1.0",
            "build>=0.10.0",
            "twine>=4.0.0",
            "pre-commit>=3.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "linkedin-games-solver=linkedin_games_scraper.solver:main",
        ],
    },
)
