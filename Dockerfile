# capalens-check in a container: docker build -t capalens-check . && docker run --rm capalens-check demo
FROM python:3.12-slim

LABEL org.opencontainers.image.title="capalens-check" \
      org.opencontainers.image.description="Read-only checks for MCP servers, OpenAPI documents, A2A Agent Cards and Agent Skills" \
      org.opencontainers.image.source="https://github.com/DefineFuture/capalens-check" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /opt/capalens-check
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY src ./src
RUN pip install ".[yaml]" && useradd --create-home --uid 10001 capalens

USER capalens
WORKDIR /work
ENTRYPOINT ["capalens-check"]
CMD ["--help"]
