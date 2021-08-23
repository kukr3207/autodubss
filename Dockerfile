FROM ubuntu:latest


RUN mkdir /app

COPY . /app

RUN apt-get update && \ 
	apt-get install -y python3 && \
	apt-get install -y python3-pip

RUN pip install -r /app/requirements.txt
RUN pip install django_apscheduler

RUN python3 /app/manage.py migrate
RUN python3 /app/manage.py makemigrations
RUN python3 /app/manage.py migrate


EXPOSE 8000

WORKDIR ./app

CMD gunicorn algo_trading.wsgi:application --bind 0.0.0.0:$PORT --preload