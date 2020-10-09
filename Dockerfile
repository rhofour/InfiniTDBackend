FROM python:3.8-buster

RUN pip install pipenv
COPY Pipfile* /tmp/InfiniTDServer/
RUN cd /tmp/InfiniTDServer && pipenv install

COPY . /tmp/InfiniTDServer
EXPOSE 8794/tcp
RUN cd /tmp/InfiniTDServer && pipenv run python -m infinitdserver
