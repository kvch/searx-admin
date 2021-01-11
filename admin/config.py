import yaml


with open('/etc/searx-admin/config.yml') as config_file:
    configuration = yaml.safe_load(config_file)
