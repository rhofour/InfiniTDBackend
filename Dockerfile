FROM python:3.8-buster

RUN pip install pipenv
# CMake is needed to build flatbuffers.
RUN apt-get update
RUN apt-get -y install cmake
ENV PROJECT_DIR /InfiniTDServer/
WORKDIR ${PROJECT_DIR}

COPY flatbuffers ${PROJECT_DIR}/flatbuffers
COPY Makefile ${PROJECT_DIR}
# Build flatc here so we don't need to rebuild it when other things change.
RUN make flatbuffers/flatc

# Install dependencies.
COPY Pipfile Pipfile.lock ${PROJECT_DIR}
RUN pipenv install --deploy

# Copy remaining project files.
COPY setup.py README.rst game_config.json ${PROJECT_DIR}
COPY infinitd_server ${PROJECT_DIR}/infinitd_server
COPY static ${PROJECT_DIR}/static

# TODO: Selectively copy what we need for this so it can be cached earlier.
# Generate flatbuffer code and compile C++ pieces.
RUN make all

EXPOSE 8794/tcp
CMD ["pipenv", "run", "python", "-u", "-m", "infinitd_server", "--verbosity=2", "--reset-battles", "--debug"]
