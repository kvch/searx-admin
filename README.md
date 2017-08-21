# searx admin

A web based management interface for searx.

## Installation & usage

### Install dependencies

Searx-admin depends on `git` and `uwsgi` tools and implemented in python.

Please make sure that dependencies of searx are installed in the same virtualenv or on the
same host searx admin is ran.

```
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Edit config

Edit `admin/config.yml`


### Start application

```
source venv/bin/activate
python admin/webapp.py
```
