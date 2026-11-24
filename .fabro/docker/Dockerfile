# Sandbox image for Fabro runs on skills: Python 3.12, git, gh and PyYAML
# (all that validate_skills.py needs).
# Build from the repo root:
#   docker build -f .fabro/docker/Dockerfile -t skills-fabro:latest .
FROM python:3.12-slim-bookworm

RUN apt-get update \
 && apt-get install -y --no-install-recommends git curl ca-certificates jq make gh \
 && rm -rf /var/lib/apt/lists/*

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_ROOT_USER_ACTION=ignore PYTHONDONTWRITEBYTECODE=1

RUN pip install --no-cache-dir pyyaml
