FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
COPY data ./data
RUN pip install --no-cache-dir . && useradd -m researcher && chown -R researcher /app
USER researcher
ENTRYPOINT ["fx-rates-lab"]
