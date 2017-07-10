import yaml


with open('admin/config.yml') as config_file:
    configuration = yaml.load(config_file)
