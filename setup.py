from setuptools import setup, find_packages

setup(
    name="rl_game_agent",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
)
