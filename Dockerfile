FROM node

ENV SERVERLESS_VERSION 1.3.0

RUN npm install serverless@${SERVERLESS_VERSION} -g

RUN apt-get update
RUN apt-get install -y \
    build-essential \
    curl \
    python-dev

RUN mkdir /root/.aws

RUN curl -s https://bootstrap.pypa.io/get-pip.py | python
RUN pip install \
    awscli \
    pytest \
    pytest-cov \
    pytest-mock \
    boto3

RUN mkdir /code
WORKDIR /code
