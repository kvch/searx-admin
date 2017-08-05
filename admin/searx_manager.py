import yaml
import subprocess
from os import listdir
from os.path import isfile, isdir, abspath, join, dirname
from signal import SIGHUP
from sys import path

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
            self.settings = yaml.load(config_file)
            self.engines = load_engines(self.settings['engines'])

    def _save(self, new_settings):
        for key, _ in self.settings[new_settings['section']].items():
            self.settings[new_settings['section']][key] = new_settings.get(key, '')

    def _save_server_and_general_settings(self, new_settings):
        self.settings['general']['debug'] = new_settings.get('debug', False)
        self.settings['general']['instance_name'] = new_settings.get('instance_name', '')
        for key, _ in self.settings['server'].items():
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

    def save_settings(self, new_settings):
        # TODO make it beautiful
        if new_settings['section'] == 'server':
            self._save_server_and_general_settings(new_settings)
        elif new_settings['section'] == 'outgoing':
            self._save_outgoing_settings(new_settings)
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

    def reload(self):
        if self.is_running():
            self._process.send_signal(SIGHUP)

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
