FROM python:3.9-slim

WORKDIR /app

#  RUN pip install flowgrid

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN pip install -e .

# Ejecuta el worker de Celery
CMD ["flowgrid", "worker"]
