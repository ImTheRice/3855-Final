FROM ubuntu:20.04
LABEL maintainer='rmaharjan1@emy.bcit.ca'

RUN apt-get update -y && \
    apt-get install -y python3 python3-pip 

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip3 install -v -r requirements.txt
    
COPY . /app/

RUN python3 createtables.py

ENTRYPOINT [ "python3" ]
CMD ["app.py"]
