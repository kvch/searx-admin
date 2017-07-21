import yaml
import subprocess
from os import listdir
from signal import SIGHUP
from sys import path

from config import configuration

path.append(configuration['searx']['root'])

from searx.engines import load_engines
from searx.languages import language_codes


class Searx(object):
    _process = None
    root_folder = ''
    settings_path = ''
    settings = None
    virtualenv_name = ''
    running = False
    languages = language_codes
    # TODO import these from searx (preferences)
    safe_search_options = [('0', 'None'),
                           ('1', 'Moderate'),
                           ('2', 'Strict')]
    autocomplete_options = [('', 'None'),
                            ('wikipedia', 'Wikipedia'),
                            ('startpage', 'StartPage'),
                            ('duckduckgo', 'DuckDuckGo'),
                            ('google', 'Google'),
                            ('dbpedia', 'DBPedia')]

    def __init__(self, root, path_to_settings, virtualenv_name):
        self.root_folder = root
        self.settings_path = path_to_settings
        self.virtualenv_name = virtualenv_name
        with open(path_to_settings) as config_file:
            self.settings = yaml.load(config_file)
            self.engines = load_engines(self.settings['engines'])

    def save_settings(self, new_settings):
        # TODO make it beautiful
        if new_settings['section'] == 'server':
            self.settings['general']['debug'] = new_settings.get('debug', False)
            self.settings['general']['instance_name'] = new_settings.get('instance_name', '')
            for key, _ in self.settings['server'].items():
                self.settings['server'][key] = new_settings.get(key, False)
        else:
            for key, _ in self.settings[new_settings['section']].items():
                self.settings[new_settings['section']][key] = new_settings.get(key, '')

        with open(self.settings_path, 'w') as config_file:
            yaml.dump(self.settings, config_file, default_flow_style=False)

    def available_themes(self):
        templates_path = self.settings['ui']['templates_path']
        if self.settings['ui']['templates_path'] == '':
            templates_path = self.root_folder + '/searx/templates'
        available_themes = []
        for filename in listdir(templates_path):
            if filename != '__common__':
                available_themes.append((filename, filename))
        return available_themes

    def reload(self):
        if self.running:
            self._process.send_signal(SIGHUP)

    def start(self):
        if self.running:
            return

        uwsgi_cmd = ['uwsgi', '--plugin', 'python', '--module', 'searx.webapp', '--master',
                     '--processes', '2', '--venv', self.virtualenv_name, '--enable-threads', '--lazy-apps',
                     '--http-socket', '{}:{}'.format(self.settings['server']['bind_address'],
                                                     self.settings['server']['port'])]

        self._process = subprocess.Popen(uwsgi_cmd, cwd=self.root_folder)
        self.running = True

    def stop(self):
        if self.running and self._process:
            self._process.kill()
            self.running = False
            self._process = None
