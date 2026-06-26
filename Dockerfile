FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Required for HF Space
RUN useradd -m -u 1000 user
USER user
ENV PATH=/home/user/.local/bin:$PATH

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY --chown=user ./backend /app/backend
COPY --chown=user ./config /app/config

# HF Space ត្រូវការ port 7860
EXPOSE 7860
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
