Documentation
=============

https://quantcollective.github.io/phocus

To build the documentation, use `tox` and push the contents of `dist/docs` to the `gh-pages` branch, or use something
like this: https://gist.github.com/cobyism/4730490

Development
===========

Building Docker
---------------
::

    docker-compose build

Getting a shell from the Docker
-------------------------------
::

    docker-compose run phocus /bin/bash


Creating a Notebook server
--------------------------
::

    docker-compose run -p 8888:8888 phocus /bin/bash -c "/opt/conda/bin/conda install jupyter -y --quiet && mkdir /opt/notebooks && /opt/conda/bin/jupyter notebook --notebook-dir=/opt/notebooks --ip='*' --port=8888 --no-browser"

You can then view the Jupyter Notebook by opening `http://localhost:8888` in your browser,
or `http://<DOCKER-MACHINE-IP>:8888` if you are using a Docker Machine VM.

Tests
-----

To run the all tests run::

    tox

To run tests inside Docker run::

    docker-compose run phocus tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox


Folder Structure
----------------

The primary entry points are `phocus/mip/mip_app.py` and `phocus/viz/dash_app.py`

The `phocus/mdp` folder contains all of the Reinforcement Learning code. It is not currently recommended for use
since it has a different scaling profile then the current use-case but it may be useful in the future.

The `phocus/traffic` folder is used to create the traffic Random Forest model. It is also not currently in use,
but is potentially very useful for scaling up traffic requests without hitting an API.


API
---
The optimizer uses Swagger and Conexion for the web server. Once the server is running you can go to /ui to view the API
UI. For example `http://localhost:8080/ui`.
