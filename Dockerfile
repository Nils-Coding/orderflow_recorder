FROM python:3.11-slim AS builder

ENV POETRY_VERSION=1.8.3 \
	PIP_DISABLE_PIP_VERSION_CHECK=1 \
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1

WORKDIR /app

# Install poetry
RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

# Copy project files
COPY pyproject.toml README.md /app/
COPY src /app/src

# Build wheel
RUN poetry build -f wheel


FROM python:3.11-slim AS runtime

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1

WORKDIR /app

# Install app wheel (this installs dependencies as well)
COPY --from=builder /app/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl

# Default command runs the recorder
CMD ["orderflow-recorder"]


