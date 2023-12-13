FROM python:3.6

ENV TINI_VERSION v0.18.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini

# Here we are using pip to install poetry instead of:
# curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python
# because there was an apparent bug with that install script that caused the installation to fail
RUN pip install -U setuptools pip poetry

WORKDIR /code

# Copy necessary files for installing dependencies
# README.rst and CHANGELOG.rst are needed as part of setup.py
#ADD setup.py README.rst CHANGELOG.rst /code/
ADD pyproject.toml /code/
RUN poetry install
ADD . .

WORKDIR /code/src
ENV PYTHONPATH=.

EXPOSE 8080

ENTRYPOINT [ "/tini", "--" ]

CMD /root/.cache/pypoetry/virtualenvs/optimizer-py3.6/bin/python phocus/app.py
