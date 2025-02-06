FROM python:3.12-slim as python-base

FROM ubuntu:22.04

# Copy Python installation from python-base
COPY --from=python-base /usr/local /usr/local

WORKDIR /workspace

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir \
    pytest \
    pytest-watch \
    debugpy

# Set noninteractive frontend to avoid tzdata prompt
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies including git, wget, and uidmap
RUN apt-get update && apt-get install -y \
    git \
    wget \
    uidmap \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Configure timezone
RUN ln -sf /usr/share/zoneinfo/UTC /etc/localtime && \
    echo "UTC" > /etc/timezone

# Install Apptainer
RUN wget https://github.com/apptainer/apptainer/releases/download/v1.0.0/apptainer_1.0.0_amd64.deb && \
    apt-get update && \
    apt-get install -y ./apptainer_1.0.0_amd64.deb && \
    rm apptainer_1.0.0_amd64.deb

CMD ["tail", "-f", "/dev/null"]