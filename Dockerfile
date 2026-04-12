FROM python:3.13-slim@sha256:35b71c1b97893609aba7ab95b35b668c88a38c30783f24cf483330fe5a8315af

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

RUN adduser --disabled-password --gecos '' appuser
USER appuser

CMD ["flask", "run", "--host=0.0.0.0"]
