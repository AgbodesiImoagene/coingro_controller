from setuptools import setup


# Requirements used for submodules
plot = ['plotly>=4.0']

hyperopt = [
    'scipy',
    'scikit-learn',
    'scikit-optimize>=0.7.0',
    'filelock',
    'joblib',
    'progressbar2',
]

databases = [
    'psycopg2',
    'PyMySQL',
]

develop = [
    'coveralls',
    'flake8',
    'flake8-tidy-imports',
    'mypy',
    'pytest',
    'pytest-asyncio',
    'pytest-cov',
    'pytest-mock',
    'pytest-random-order',
]

jupyter = [
    'jupyter',
    'nbstripout',
    'ipykernel',
    'nbconvert',
]

all_extra = plot + develop + jupyter + hyperopt + databases

setup(
    tests_require=[
        'pytest',
        'pytest-asyncio',
        'pytest-cov',
        'pytest-mock',
    ],
    install_requires=[
        # from requirements.txt
        'ccxt>=1.83.12,<1.90.*',
        'cryptography',
        'aiohttp',
        'SQLAlchemy',
        'SQLAlchemy-Utils',
        'python-telegram-bot>=13.4',
        'arrow>=0.17.0',
        'cachetools',
        'requests',
        'urllib3',
        'jsonschema',
        'TA-Lib',
        'pandas-ta',
        'technical',
        'tabulate',
        'pycoingecko',
        'py_find_1st',
        'python-rapidjson',
        'orjson',
        'sdnotify',
        'colorama',
        'jinja2',
        'questionary',
        'prompt-toolkit',
        'numpy',
        'pandas',
        'tables',
        'blosc',
        'fastapi',
        'uvicorn',
        'psutil',
        'pyjwt',
        'aiofiles',
        'schedule',
        'python-dateutil',
        'kubernetes>=24.2.0',
        'coingro',
    ],
    extras_require={
        'dev': all_extra,
        'plot': plot,
        'jupyter': jupyter,
        'hyperopt': hyperopt,
        'all': all_extra,
    },
)
