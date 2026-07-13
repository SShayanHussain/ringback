FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app
COPY pyproject.toml ./
COPY ringback_agent ./ringback_agent
RUN pip install --no-cache-dir .

EXPOSE 8001
# In-process, single service (free-tier packing, PLAYBOOK §12.7). No forked worker -> no gRPC-fork class.
CMD ["uvicorn", "ringback_agent.service:app", "--host", "0.0.0.0", "--port", "8001"]
