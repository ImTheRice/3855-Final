FROM ubuntu:20.04
LABEL maintainer='rmaharjan1@emy.bcit.ca'

RUN apt-get update -y && \
    apt-get install -y python3 python3-pip sqlite3

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip3 install -r requirements.txt

COPY . /app/

RUN mkdir -p /data && chmod 777 /data

RUN python3 create_db.py

ENTRYPOINT [ "python3" ]
CMD ["app.py"]
