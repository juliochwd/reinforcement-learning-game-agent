from setuptools import setup, find_packages

setup(
    name="rl_game_agent",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    entry_points={
        'console_scripts': [
            'run-hpt = src.rl_agent.hyperparameter_search:main',
            'train-final = train_final_model:main',
        ],
    },
)
