set -e
flake8 --radon-max-cc 10 --ignore=E501,E302,E722,W503
mypy .
bandit -r -s B101 .
# pytest -n auto --reruns 5
