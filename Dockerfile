FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# collectstatic doesn't use the secret key, but settings require one to be set.
RUN SECRET_KEY=build-only python manage.py collectstatic --noinput

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed_demo && gunicorn confighub.wsgi --bind 0.0.0.0:8000 --workers 3 --access-logfile -"]
