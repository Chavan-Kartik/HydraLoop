# Backend image for the HydraLoop command center.
#
# This serves the FastAPI app. It deliberately does not install torch: the only
# component that imports it is the sequence model inside the defence-stack
# ensemble, which is reachable through the `stack` and `evaluate` CLI commands
# and never from an API route. Dropping that one wheel takes roughly 490 MB out
# of the image, which is the difference between building on a free tier and not.
# The test-only dependencies are filtered for the same reason. requirements.txt
# stays the single pinned source; the filter here is the only place that departs
# from it, so there is no second dependency list to drift.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860

WORKDIR /app

# LightGBM links against the OpenMP runtime, which the slim base image omits.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
# The pytorch index goes with torch. Leaving it in makes pip query that index
# for every other package too, which slows the build and risks resolving a
# different numpy or scipy build than the pins were measured against.
RUN grep -vE '^(--extra-index-url|torch==|pytest==|pytest-cov==|hypothesis==|httpx==|ruff==|python-docx==)' \
    requirements.txt > /tmp/api-requirements.txt \
    && pip install --upgrade pip \
    && pip install -r /tmp/api-requirements.txt

COPY src/ ./src/
COPY catalog/ ./catalog/
COPY configs/ ./configs/
COPY reports/ ./reports/

# --no-deps because pyproject declares torch as a runtime dependency; resolving
# it here would reinstall the wheel the filter above just removed.
RUN pip install --no-deps -e .

# Managed hosts inject PORT and the CMD below honours it; 7860 is only the
# fallback for a plain `docker run` with nothing set.
EXPOSE 7860
CMD ["sh", "-c", "uvicorn hydraloop.api.app:app --host 0.0.0.0 --port ${PORT}"]
