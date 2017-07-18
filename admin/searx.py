import yaml
from os import listdir, system


class Searx(object):
    settings_path = ''
    settings = None
    root_folder = None
    pid = None
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

        with open(self.settings_path) as config_file:
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
        pass

    def start(self):
        pass

    def stop(self):
        pass

