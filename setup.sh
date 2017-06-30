apt-get update

apt-get install -y --no-install-recommends --no-install-suggests \
  gcc \
  python3 \
  python3-dev \
  python3-pip \
  python3-setuptools \
  libpython3.5 \
  libpcre3 \
  libpcre3-dev \
  supervisor

pip3 install --upgrade pip
pip3 install wheel
pip3 install uwsgi
pip3 install flask

apt-get remove -y  \
  gcc \
  python3-dev \
  python3-pip \
  libpcre3-dev

apt -y autoremove
apt-get clean
rm -rf /var/lib/apt/lists/*
