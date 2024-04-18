FROM ubuntu:20.04
LABEL maintainer='rmaharjan1@emy.bcit.ca'

RUN apt-get update -y && \
    apt-get install -y python3 python3-pip

# Copying requirements file
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip3 install -r requirements.txt

# Copying the rest of the application
COPY . /app/

ENTRYPOINT [ "python3" ]
CMD ["app.py"]