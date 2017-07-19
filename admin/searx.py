import yaml
import subprocess
from os import listdir
from signal import SIGHUP


class Searx(object):
    settings_path = ''
    settings = None
    root_folder = None
    process = None
    running = False
    safe_search_options = [('0', 'None'),
                           ('1', 'Moderate'),
                           ('2', 'Strict')]
    autocomplete_options = [('', 'None'),
                            ('wikipedia', 'Wikipedia'),
                            ('startpage', 'StartPage'),
                            ('duckduckgo', 'DuckDuckGo'),
                            ('google', 'Google'),
                            ('dbpedia', 'DBPedia')]

    def __init__(self, root_folder, settings_path):
        self.root_folder = root_folder
        self.settings_path = settings_path
        with open(settings_path) as config_file:
            self.settings = yaml.load(config_file)

    def save_settings(self, new_settings):
        if new_settings['section'] == 'server':
            self.settings['general']['debug'] = 'debug' in new_settings
            self.settings['general']['instance_name'] = new_settings['instance_name']
            for key, _ in self.settings['server'].items():
                self.settings['server'][key] = new_settings[key]
        else:
            for key, _ in self.settings[settings['section']].items():
                self.settings[settings['section']][key] = new_settings[key]

        with open(self.settings_path, 'w') as config_file:
            yaml.dump(self.settings, config_file)

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
            self.process.send_signal(SIGHUP)

    def start(self):
        if self.running:
            return

        # TODO pass virtual env as a parameter
        uwsgi_cmd = ['uwsgi', '--plugin', 'python', '-w', 'searx.webapp', '--master',
                     '--processes', '2', '-H', 'venv', '--enable-threads', '--lazy-apps',
                     '--http-socket', '{}:{}'.format(self.settings['server']['bind_address'],
                                                     self.settings['server']['port'])]

        self.process = subprocess.Popen(uwsgi_cmd, cwd=self.root_folder)
        self.running = True

    def stop(self):
        if self.running and self.process:
            self.process.kill()
            self.running = False
            self.process = None
