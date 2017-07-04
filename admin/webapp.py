from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from flask_security import Security, SQLAlchemyUserDatastore
from os.path import isfile

from config import configuration

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = configuration['app']['sqlite_path']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(120))

    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        self.password = password

    def __repr__(self):
        return 'Admin <{} {}>'.format(self.name, self.email)


user_datastore = SQLAlchemyUserDatastore(db, Admin, None)
security = Security(app, user_datastore)


@app.route('/')
def index():
    return 'hello'


def _create_db_if_missing():
    if not isfile(configuration['app']['sqlite_path']):
        db.create_all()


def run():
    app.run(port=configuration['app']['port'],
            debug=configuration['app']['debug'])


if __name__ == '__main__':
    _create_db_if_missing()
    run()
