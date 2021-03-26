FROM fedora:33

# Install DNF dependencies
RUN dnf groupinstall -y "Development Tools" "Development Libraries"
RUN dnf install -y cmake sqlite-devel
# Install pyenv
RUN curl -L https://github.com/pyenv/pyenv-installer/raw/master/bin/pyenv-installer | bash
ENV PATH="/root/.pyenv/bin:${PATH}"
# Use pyenv to install Python 3.8.8
RUN pyenv install 3.8.8
RUN pyenv global 3.8.8
RUN pyenv rehash
RUN pip install pipenv
ENV PROJECT_DIR /InfiniTDServer/
WORKDIR ${PROJECT_DIR}

COPY flatbuffers ${PROJECT_DIR}/flatbuffers
COPY Makefile ${PROJECT_DIR}
# Prevent us from accidentally picking up binaries.
RUN make clean
# Build flatc here so we don't need to rebuild it when other things change.
RUN make flatbuffers/flatc

# Install dependencies.
COPY Pipfile Pipfile.lock ${PROJECT_DIR}
RUN pipenv install --deploy

# Copy remaining project files.
COPY setup.py README.md game_config.json ${PROJECT_DIR}
COPY infinitd_server ${PROJECT_DIR}/infinitd_server
COPY static ${PROJECT_DIR}/static

# TODO: Selectively copy what we need for this so it can be cached earlier.
# Generate flatbuffer code and compile C++ pieces.
RUN make all

EXPOSE 8794/tcp
ENV DOMAIN=infinitd.rofer.me
CMD [   "pipenv", "run", "python", "-u", "-m", "infinitd_server", "--verbosity=2", "--reset-battles", \
        "--debug", "--ssl_cert", "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem", \
        "--ssl_key", "/etc/letsencrypt/live/${DOMAIN}/privkey.pem" ]
