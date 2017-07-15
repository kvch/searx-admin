from os import listdir
from os.path import isfile
import yaml

from flask import Flask, render_template, request, redirect, url_for
from flask_mail import Mail
from flask_security import Security, SQLAlchemySessionUserDatastore, login_required

from config import configuration
from database import db_session, init_db
from model import User, Role


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

with open(configuration['searx']['path_to_settings']) as config_file:
    searx_settings = yaml.load(config_file)


@app.before_first_request
def _create_db_if_missing():
    if not isfile(configuration['app']['sqlite_path'][len('sqlite////'):]):
        init_db()
        user_datastore.create_user(email='admin@localhost', password='password')
        db_session.commit()


@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/instance')
@login_required
def server():
    return render_template('server.html',
                           instance_name=searx_settings['general']['instance_name'],
                           debug=searx_settings['general']['debug'],
                           **searx_settings['server'])


@app.route('/search')
@login_required
def search():
    # TODO better option retrieval
    safe_search_options = [('0', 'None'),
                           ('1', 'Moderate'),
                           ('2', 'Strict')]
    autocomplete_options = [('', 'None'),
                            ('wikipedia', 'Wikipedia'),
                            ('startpage', 'StartPage'),
                            ('duckduckgo', 'DuckDuckGo'),
                            ('google', 'Google'),
                            ('dbpedia', 'DBPedia')]
    return render_template('search.html',
                           instance_name=searx_settings['general']['instance_name'],
                           safe_search_options=safe_search_options,
                           autocomplete_options=autocomplete_options,
                           **searx_settings['search'])


def _setup_locales_to_display():
    locales = []
    for key, val in searx_settings['locales'].items():
        locales.append((key, val))
    locales.append(('', 'Default'))
    return locales


def _get_available_themes():
    templates_path = searx_settings['ui']['templates_path']
    if searx_settings['ui']['templates_path'] == '':
        templates_path = configuration['searx']['path_to_settings'][:-len('settings.yml')] + '/templates'
    available_themes = []
    for filename in listdir(templates_path):
        if filename != '__common__':
            available_themes.append((filename, filename))
    return available_themes


@app.route('/ui')
@login_required
def ui():
    locales = _setup_locales_to_display()
    available_themes = _get_available_themes()
    return render_template('ui.html',
                           instance_name=searx_settings['general']['instance_name'],
                           locales=locales,
                           available_themes=available_themes,
                           **searx_settings['ui'])


@app.route('/engines')
@login_required
def engines():
    return render_template('engines.html',
                           instance_name=searx_settings['general']['instance_name'],
                           engines=searx_settings['engines'])



@app.route('/settings')
@login_required
def settings():
    return 'settings'


def _save_searx_settings(settings):
    if settings['section'] == 'server':
        searx_settings['general']['debug'] = 'debug' in settings
        searx_settings['general']['instance_name'] = settings['instance_name']
        for key, _ in searx_settings['server'].items():
            searx_settings['server'][key] = settings[key]
    else:
        for key, _ in searx_settings[settings['section']].items():
            searx_settings[settings['section']][key] = settings[key]

    with open(configuration['searx']['path_to_settings'], 'w') as config_file:
        yaml.dump(searx_settings, config_file)


@app.route('/save', methods=['POST'])
@login_required
def save():
    if request.form is None or 'section' not in request.form:
        return redirect(url_for('index'))

    _save_searx_settings(request.form)

    return redirect(url_for(request.form['section']))


def run():
    app.run(port=configuration['app']['port'],
            debug=configuration['app']['debug'])


if __name__ == '__main__':
    run()
