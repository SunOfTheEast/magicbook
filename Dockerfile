FROM pgvector/pgvector:pg16

COPY scws-master.tar.gz /tmp/scws-master.tar.gz

RUN apt-get update && apt-get install -y \
    autoconf \
    curl \
    libtool \
    libtool-bin \
    postgresql-server-dev-16 \
    build-essential \
    git \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /scws \
 && tar -xzf /tmp/scws-master.tar.gz -C /scws --strip-components=1 \
 && cd /scws \
 && sed -i '24,26d' Makefile.am \
 && autoreconf -ifv \
 && ./configure \
 && make install


RUN git clone https://github.com/amutu/zhparser.git /zhparser \
 && cd /zhparser \
 && make \
 && make install
