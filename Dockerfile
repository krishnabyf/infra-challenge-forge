FROM python:3.12-slim

RUN useradd --create-home --uid 10001 forge
WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

USER forge
ENTRYPOINT ["infra-forge"]

