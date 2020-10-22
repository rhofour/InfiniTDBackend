FROM python:3.8-buster

RUN pip install pipenv
ENV PROJECT_DIR /InfiniTDServer/
WORKDIR ${PROJECT_DIR}

COPY Pipfile* ${PROJECT_DIR}
RUN pipenv install --deploy

COPY . ${PROJECT_DIR}

EXPOSE 8794/tcp
CMD ["pipenv", "run", "python", "-u", "-m", "infinitdserver", "--verbosity=2"]
