import yaml
import subprocess
from os import listdir
from os.path import isfile, isdir, abspath, join, dirname
from signal import SIGHUP
from shutil import copy
from sys import path

from requests import get

from config import configuration

path.append(configuration['searx']['root'])

from searx.engines import load_engines
from searx.languages import language_codes
from searx import autocomplete


BASE_DIR = abspath(dirname(__file__))
REFERENCE_SETTINGS_PATH = join(BASE_DIR, 'reference_settings.yml')
EDITABLE_SETTINGS_PATH = join(BASE_DIR, 'searx_generated_settings.yml')
UWSGI_CONFIG_PATH = join(BASE_DIR, 'searx_uwsgi.ini')
UWSGI_INI_TPL = '''
[uwsgi]
# disable logging for privacy
#disable-logging = true

# Number of workers (usually CPU count)
workers = 2

http-socket = {http_socket}
socket = 127.0.0.1:7777

master = true
plugin = python
lazy-apps = true
enable-threads = true

# Module to import
module = searx.webapp

base = {searx_dir}
pythonpath = {searx_dir}
chdir = {searx_dir}/searx
'''


class Searx(object):
    _process = None
    root_folder = ''
    settings_path = ''
    settings = None
    uwsgi_extra_args = []
    languages = language_codes
    safe_search_options = [('0', 'None'),
                           ('1', 'Moderate'),
                           ('2', 'Strict')]
    autocomplete_options = zip(list(autocomplete.backends.keys()) + [''],
                               list(autocomplete.backends.keys()) + ['-'])

    def __init__(self, root, uwsgi_extra_args):
        self.root_folder = root
        self.uwsgi_extra_args = uwsgi_extra_args
        with open(REFERENCE_SETTINGS_PATH) as config_file:
            config = config_file.read()
            self.settings = yaml.load(config)
            self.engines = load_engines(self.settings['engines'])
            if isfile(EDITABLE_SETTINGS_PATH):
                with open(EDITABLE_SETTINGS_PATH) as config_file2:
                    self._merge_settings(yaml.load(config_file2.read()))
            else:
                with open(EDITABLE_SETTINGS_PATH, 'w') as outfile:
                    outfile.write(config)

    def _merge_settings(self, new_settings):
        for k, s in new_settings.items():
            if k == 'engines':
                continue
            for kk, c in s.items():
                self.settings[k][kk] = c

        editable_engines = {e['name']: e for e in new_settings['engines']}
        for i, e in enumerate(self.settings['engines']):
            if e['name'] in editable_engines:
                self.settings['engines'][i] = editable_engines[e['name']]

    def _save(self, new_settings):
        for key in self.settings[new_settings['section']]:
            new_val = new_settings.get(key, '')
            val_type = type(self.settings[new_settings['section']][key])
            if val_type != type(new_val):
                try:
                    new_val = val_type(new_val)
                except:
                    print("Failed to parse settings attribute", section, '->', val_name)
                    continue
            self.settings[new_settings['section']][key] = new_val

    def _save_server_and_general_settings(self, new_settings):
        self.settings['general']['debug'] = 'debug' in new_settings
        self.settings['general']['instance_name'] = new_settings.get('instance_name', '')
        for key in self.settings['server']:
            self.settings['server'][key] = new_settings.get(key, False)
        self._save_uwsgi_ini()

    def _save_uwsgi_ini(self):
        # save uwsgi.ini too
        with open(UWSGI_CONFIG_PATH, 'w') as outfile:
            outfile.write(UWSGI_INI_TPL.format(
                http_socket = '{}:{}'.format(
                    self.settings['server']['bind_address'],
                    self.settings['server']['port'],
                ),
                searx_dir = self.root_folder,
            ))

    def _save_outgoing_settings(self, new_settings):
        self._save(new_settings)
        self.settings['outgoing']['source_ips'] = new_settings['source_ips'].split(', ')

    def _save_engine(self, engine):
        for e2 in self.settings['engines']:
            if e2['name'] == engine.name:
                for attr in dir(engine):
                    if attr in e2:
                        e2[attr] = getattr(engine, attr)
                print("engine settings saved")
                break

    def save_settings(self, new_settings):
        # TODO make it beautiful
        if new_settings['section'] == 'server':
            self._save_server_and_general_settings(new_settings)
        elif new_settings['section'] == 'outgoing':
            self._save_outgoing_settings(new_settings)
        if new_settings['section'] == 'engine':
            self._save_engine(new_settings['engine'])
        else:
            self._save(new_settings)

        with open(EDITABLE_SETTINGS_PATH, 'w') as config_file:
            yaml.dump(self.settings, config_file, default_flow_style=False)

    def available_themes(self):
        templates_path = self.settings['ui']['templates_path']
        if self.settings['ui']['templates_path'] == '':
            templates_path = self.root_folder + '/searx/templates'
        available_themes = []
        if not isdir(templates_path):
            # TODO log error
            return None
        for filename in listdir(templates_path):
            if filename != '__common__':
                available_themes.append((filename, filename))
        return available_themes

    def restore_defaults(self):
        copy(REFERENCE_SETTINGS_PATH, EDITABLE_SETTINGS_PATH)
        self.reload()

    def reload(self):
        if self.is_running():
            self._process.send_signal(SIGHUP)
        else:
            self.start()

    def update(self):
        subprocess.Popen(
            ['git', 'pull', 'origin', 'master'],
            cwd=self.root_folder,
        ).wait()
        try:
            new_reference_settings = get('https://raw.githubusercontent.com/kvch/searx-admin/master/admin/reference_settings.yml').text
            if new_reference_settings:
                with open(REFERENCE_SETTINGS_PATH, 'w') as outfile:
                    outfile.write(new_reference_settings.encode('utf-8'))
        except Exception as e:
            print('Failed to fetch new references settings.yml', e)

        self.reload()

    def is_running(self):
        if self._process is None:
            return False

        self._process.poll()
        return self._process.returncode is None

    def start(self):
        if self.is_running():
            return

        if not isfile(UWSGI_CONFIG_PATH):
            self._save_uwsgi_ini()

        uwsgi_cmd = ['uwsgi', '--ini', UWSGI_CONFIG_PATH]
        uwsgi_cmd.extend(self.uwsgi_extra_args)

        self._process = subprocess.Popen(
            uwsgi_cmd,
            cwd=self.root_folder,
            env={'SEARX_SETTINGS_PATH': EDITABLE_SETTINGS_PATH},
        )

    def stop(self):
        if self.is_running():
            self._process.terminate()
        if self.is_running():
            self._process.kill()
        if not self.is_running():
            self._process = None

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()
