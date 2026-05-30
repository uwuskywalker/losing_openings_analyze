FROM python:3.13.5-slim
WORKDIR /code
RUN RUN pip install uv
RUN RUN uv pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]