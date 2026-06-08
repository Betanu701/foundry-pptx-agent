FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY templates ./templates
COPY examples ./examples

RUN pip install --no-cache-dir .

ENV HOST=0.0.0.0
ENV PORT=8088
EXPOSE 8088

CMD ["python", "-m", "foundry_pptx_agent.app"]

