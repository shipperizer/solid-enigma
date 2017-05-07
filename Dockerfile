FROM python:3.6-slim

RUN apt-get update && \
	apt-get -y --no-install-recommends install \
		build-essential \
		libevent-dev \
	&& apt-get clean && rm -rf /var/lib/apt/lists/*

COPY Makefile requirements.txt /var/app/

WORKDIR /var/app

RUN make install

COPY *.py /var/app/

CMD ["bash"]
