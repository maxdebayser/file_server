FROM ubuntu:16.04

MAINTAINER mbayser@br.ibm.com

WORKDIR /root/

RUN apt-get update -y && apt-get install -y \
  bzip2 \
  gcc \
  nginx \
  python3 \
  python3-dev \
  python3-pip \
  supervisor && pip3 install uwsgi flask && apt-get remove -y gcc python3-dev python3-pip && apt-get clean
  
COPY app.py /root/app.py
COPY uwsgi.ini /root/uwsgi.ini
COPY supervisord.conf /root/supervisord.conf
COPY nginx.conf /etc/nginx/nginx.conf

VOLUME /files
VOLUME /input_files

RUN mkdir /sockets

CMD /usr/bin/supervisord
