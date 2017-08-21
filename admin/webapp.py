import sys
from os.path import isfile

from flask import Flask, render_template, request, redirect, url_for
from flask_mail import Mail
from flask_security import Security, SQLAlchemySessionUserDatastore, login_required, user_registered

from config import configuration
from database import db_session, init_db
from model import User, Role
from searx_manager import Searx


app = Flask(__name__)
app.secret_key = configuration['app']['secretkey']

app.config['SECURITY_PASSWORD_SALT'] = configuration['app']['secretkey']
app.config['SECURITY_REGISTERABLE'] = True
app.config['SECURITY_SEND_REGISTER_EMAIL'] = False

mail = Mail(app)
user_datastore = SQLAlchemySessionUserDatastore(db_session, User, Role)
security = Security(app, user_datastore)
instance = Searx(**configuration['searx'])
is_user_missing = True


def render(template_name, **kwargs):
    kwargs['instance'] = instance
    kwargs['menu_items'] = (
        ('server', 'Instance'),
        ('search', 'Search'),
        ('ui', 'User interface'),
        ('outgoing', 'Outgoing requests'),
        ('engines', 'Engines'),
    )
    return render_template(template_name, **kwargs)


@app.before_request
def _create_user_if_missing():
    global is_user_missing
    accessible_paths = [
            url_for('security.register'),
            url_for('static', filename='css/main.css'),
            url_for('static', filename='css/material.min.css'),
            url_for('static', filename='js/material.min.js'),
    ]
    if is_user_missing and request.path not in accessible_paths:
        return redirect(url_for('security.register'))


@user_registered.connect_via(app)
def user_registered_sighandler(sender, **extra):
    global is_user_missing
    is_user_missing = False


@app.route('/')
@login_required
def index():
    return render('manage.html',
                  bind_address=instance.settings['server']['bind_address'],
                  port=instance.settings['server']['port'])


@app.route('/instance')
@login_required
def server():
    return render('server.html',
                  instance_name=instance.settings['general']['instance_name'],
                  debug=instance.settings['general']['debug'],
                  **instance.settings['server'])


@app.route('/search')
@login_required
def search():
    return render('search.html',
                  safe_search_options=instance.safe_search_options,
                  autocomplete_options=instance.autocomplete_options,
                  languages=instance.languages,
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
    return render('ui.html',
                  locales=locales,
                  available_themes=available_themes,
                  **instance.settings['ui'])


@app.route('/outgoing')
@login_required
def outgoing():
    return render('outgoing.html', **instance.settings['outgoing'])


@app.route('/engines')
@login_required
def engines():
    return render('engines.html', engines=instance.engines)


@app.route('/engine/<engine_name>/edit', methods=['GET', 'POST'])
@login_required
def edit_engine(engine_name):
    skip_attrs = ('name', 'continuous_errors', 'paging', 'suspend_end_time')
    engine = instance.engines[engine_name]
    attrs = []
    type_map = {str: 'str', float: 'float', int: 'float', bool: 'bool'}
    for attr in dir(engine):
        if attr.startswith('_') or attr in skip_attrs:
            continue
        attr_value = getattr(engine, attr)
        attr_type = type(attr_value)
        if attr_type not in (str, int, float, bool, unicode):
            continue
        if request.method == 'POST':
            try:
                attr_value = attr_type(request.form[attr])
                setattr(engine, attr, attr_value)
            except:
                print("attr not found or type mismatched", attr, attr_type, request.form.get(attr))
        attrs.append((attr, attr_value, type_map[attr_type]))
    if request.method == 'POST':
        instance.save_settings({'section': 'engine', 'engine': engine})
        instance.reload()
    return render('edit_engine.html', engine=engine, engine_attrs=attrs, isinstance=isinstance)


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
    return redirect(url_for('index'))


@app.route('/stop')
@login_required
def stop_instance():
    instance.stop()
    return redirect(url_for('index'))


@app.route('/restore_defaults')
@login_required
def restore_defaults():
    instance.restore_defaults()
    return redirect(url_for('index'))


@app.route('/reload')
@login_required
def reload_instance():
    instance.reload()
    return redirect(url_for('index'))


@app.route('/update')
@login_required
def update():
    instance.update()
    return redirect(url_for('index'))


def _check_db():
    global is_user_missing
    try:
        user = User.query.first()
        if user:
            is_user_missing = False
    except:
        pass


def run():
    init_db()
    _check_db()
    with instance:
        app.run(port=configuration['app']['port'], debug=False)


if __name__ == '__main__':
    run()
