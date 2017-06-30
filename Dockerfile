FROM nginx_lua

MAINTAINER mbayser@br.ibm.com

WORKDIR /root/

WORKDIR /
ADD setup.sh /root
RUN /bin/bash /root/setup.sh
  
COPY app.py /root/app.py
COPY uwsgi.ini /root/uwsgi.ini
COPY supervisord.conf /root/supervisord.conf
COPY nginx.conf /etc/nginx/nginx.conf

VOLUME /files
VOLUME /input_files

RUN mkdir /sockets

WORKDIR /root/
CMD /usr/bin/supervisord
