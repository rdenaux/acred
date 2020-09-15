uWSGI configs and launchers
---------------------------

This folder contains various `wsgi-xxx-api.ini` and `wsgi-xxx-api.py`
files.

[uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/index.html) is a
special protocol used to interface between web-servers like nginx and
web-apps in python.

The `.ini` files are used to launch uWSGI processes, while the `.py`
files run the python process to be served. 

In acred, the `uwsgi` is only executed when launching an API via
docker. This is usually only needed for integration testing and in
production. During development you can launch flask app in dev mode by
calling the `runsrv.py` command.

The `uwsgi` command is executed when launching a `docker-compose`
service, so check out the `docker-compose.yml` and points to the
relevant `.ini` file. The `.ini` file points to the `.py` file which
should have been previously copied to the container (this is typically
done in the relevant dockerfile).


