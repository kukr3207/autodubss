FROM ubuntu:latest


RUN mkdir /app

COPY . /app

RUN apt-get update && \ 
	apt-get install -y python3 && \
	apt-get install -y python3-pip

RUN pip install -r /app/requirements.txt

RUN python3 /app/manage.py makemigrations
RUN python3 /app/manage.py migrate


EXPOSE 8000

WORKDIR ./app

CMD gunicorn hello_django.wsgi:application --bind 0.0.0.0:$PORT