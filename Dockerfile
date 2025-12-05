FROM python:3.10-slim-bullseye
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install \
    --no-cache-dir \
    --default-timeout=120 \
    --retries=10 \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r requirements.txt

COPY bot /app
ENTRYPOINT ["bash", "-c", "pybabel compile -d locales -D bot; alembic upgrade head; python main.py"]
