from .config import load_uci, load_yaml
import os
import argparse
import sys
import logging
from .mqttled import mqttled

LOG_FORMAT = '%(asctime)s %(levelname)s: %(message)s'

def main():
    argp = argparse.ArgumentParser(description='LED to MQTT')
    argp.add_argument('-y','--yaml', help='use a yaml config file e.g. /config/mqttled.yml', action='store_true')
    argp.add_argument('conffile', help='path to configuration file, defaults to /etc/config/mqttled', default='mqttled')
    args = argp.parse_args()
    
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format=LOG_FORMAT)
    
    if args['yaml']:
        config = load_yaml(args['yamlfile'])
    else:
        config = log_uci(args[''])
    
    mqttled(config)
if __name__ == '__main__':
    main()