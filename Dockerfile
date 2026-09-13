FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Chạy root: nested overlay2-in-Codespaces không cho non-root exec (đã confirm qua test)
# RUN useradd -m -u 1000 user
# USER user
# ENV PATH=/home/user/.local/bin:$PATH

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY ./backend /app/backend
COPY ./config /app/config

# HF Space cần port 7860
EXPOSE 7860
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
