import sys
from os.path import isfile

from flask import Flask, render_template, request, redirect, url_for
from flask_mail import Mail
from flask_security import Security, SQLAlchemySessionUserDatastore, login_required

from config import configuration
from database import db_session, init_db
from model import User, Role
from searx_manager import Searx

from sys import path
path.append(configuration['searx']['root'])

from searx.languages import language_codes as languages


app = Flask(__name__)
app.secret_key = configuration['app']['secretkey']

app.config['SECURITY_PASSWORD_SALT'] = configuration['app']['secretkey']

app.config['MAIL_SERVER'] = configuration['mail']['server']
app.config['MAIL_PORT'] = configuration['mail']['port']
app.config['MAIL_USE_SSL'] = configuration['mail']['use_ssl']
app.config['MAIL_USERNAME'] = configuration['mail']['user']
app.config['MAIL_PASSWORD'] = configuration['mail']['password']

mail = Mail(app)
user_datastore = SQLAlchemySessionUserDatastore(db_session, User, Role)
security = Security(app, user_datastore)
instance = Searx(**configuration['searx'])


@app.before_first_request
def _create_db_if_missing():
    if not isfile(configuration['app']['sqlite_path'][len('sqlite////'):]):
        init_db()
        user_datastore.create_user(email='admin@localhost', password='password')
        db_session.commit()


@app.route('/')
@login_required
def index():
    return render_template('manage.html',
                           instance_running=instance.running,
                           bind_address=instance.settings['server']['bind_address'],
                           port=instance.settings['server']['port'])


@app.route('/instance')
@login_required
def server():
    return render_template('server.html',
                           instance_name=instance.settings['general']['instance_name'],
                           debug=instance.settings['general']['debug'],
                           **instance.settings['server'])


@app.route('/search')
@login_required
def search():
    return render_template('search.html',
                           safe_search_options=instance.safe_search_options,
                           autocomplete_options=instance.autocomplete_options,
                           languages=languages,
                           **instance.settings['search'])


def _setup_locales_to_display():
    locales = []
    for key, val in instance.settings['locales'].items():
        locales.append((key, val))
    locales.append(('', 'Default'))
    return locales


@app.route('/ui')
@login_required
def ui():
    locales = _setup_locales_to_display()
    available_themes = instance.available_themes()
    return render_template('ui.html',
                           locales=locales,
                           available_themes=available_themes,
                           **instance.settings['ui'])


@app.route('/outgoing')
@login_required
def outgoing():
    return render_template('outgoing.html', **instance.settings['outgoing'])


@app.route('/engines')
@login_required
def engines():
    return render_template('engines.html', engines=instance.settings['engines'])


@app.route('/settings')
@login_required
def settings():
    return 'settings'


@app.route('/save', methods=['POST'])
@login_required
def save():
    if request.form is None or 'section' not in request.form:
        return redirect(url_for('index'))

    instance.save_settings(request.form)
    instance.reload()

    return redirect(url_for(request.form['section']))


@app.route('/start')
@login_required
def start_instance():
    instance.start()
    return render_template('manage.html',
                           instance_running=instance.running,
                           bind_address=instance.settings['server']['bind_address'],
                           port=instance.settings['server']['port'])



@app.route('/stop')
@login_required
def stop_instance():
    instance.stop()
    return render_template('manage.html',
                           instance_running=instance.running,
                           bind_address=instance.settings['server']['bind_address'],
                           port=instance.settings['server']['port'])



@app.route('/reload')
@login_required
def reload_instance():
    instance.reload()
    return render_template('manage.html',
                           instance_running=instance.running,
                           bind_address=instance.settings['server']['bind_address'],
                           port=instance.settings['server']['port'])



def run():
    app.run(port=configuration['app']['port'],
            debug=configuration['app']['debug'])


if __name__ == '__main__':
    run()
