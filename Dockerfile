# First stage: Get Python from official image
FROM python:3.12-slim as python-base

# Second stage: Build from Ubuntu
FROM ubuntu:22.04

# Copy Python installation from python-base
COPY --from=python-base /usr/local /usr/local

# Set noninteractive frontend to avoid tzdata prompt
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies including git, wget, and uidmap
RUN apt-get update && apt-get install -y \
    git \
    wget \
    uidmap \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Install Apptainer with version pinning
ARG APPTAINER_VERSION=1.0.0
RUN wget https://github.com/apptainer/apptainer/releases/download/v${APPTAINER_VERSION}/apptainer_${APPTAINER_VERSION}_amd64.deb && \
    apt-get update && \
    apt-get install -y ./apptainer_${APPTAINER_VERSION}_amd64.deb && \
    rm apptainer_${APPTAINER_VERSION}_amd64.deb

# Set up working directory
WORKDIR /c4league

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-watch \
    debugpy
