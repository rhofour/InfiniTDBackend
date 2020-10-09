FROM python:3.8-buster

RUN pip install pipenv
ENV PROJECT_DIR /tmp/InfiniTDServer/
WORKDIR ${PROJECT_DIR}

COPY Pipfile* ${PROJECT_DIR}
RUN pipenv install --deploy

COPY . ${PROJECT_DIR}

EXPOSE 8794/tcp
CMD ["pipenv",  "run", "python", "-m", "infinitdserver"]
