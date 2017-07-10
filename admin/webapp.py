from os.path import isfile

from flask import Flask, render_template
from flask_security import Security, SQLAlchemySessionUserDatastore, login_required

from config import configuration
from database import db_session, init_db
from model import User, Role


app = Flask(__name__)
app.secret_key = configuration['app']['secretkey']
app.config['SECURITY_PASSWORD_SALT'] = configuration['app']['secretkey']

user_datastore = SQLAlchemySessionUserDatastore(db_session, User, Role)
security = Security(app, user_datastore)


@app.before_first_request
def _create_db_if_missing():
    if not isfile(configuration['app']['sqlite_path'][len('sqlite////'):]):
        init_db()
        user_datastore.create_user(email='admin@localhost', password='password')
        db_session.commit()





@app.route('/')
def index():
    return 'hello'




def run():
    app.run(port=configuration['app']['port'],
            debug=configuration['app']['debug'])


if __name__ == '__main__':
    run()
