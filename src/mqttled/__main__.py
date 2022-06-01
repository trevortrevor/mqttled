#!/usr/bin/env python3

from .config import load_uci, load_yaml
import os
import argparse
import sys
import logging
from .ledHost import ledHost
import signal

LOG_FORMAT = '%(asctime)s %(levelname)s: %(message)s'

def setup():
    argp = argparse.ArgumentParser(description='LED to MQTT')
    argp.add_argument('-y','--yaml', help='use a yaml config file e.g. /config/mqttled.yml', action='store_true')
    argp.add_argument('conffile', help='path to configuration file, defaults to /etc/config/mqttled', nargs='?', default='mqttled')
    argp.add_argument('-d','--debug', help="Debug", action='store_true')
    args = argp.parse_args()
    
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format=LOG_FORMAT)
    
    if args.yaml:
        config = load_yaml(args.yaml)
    else:
        config = load_uci(args.conffile)
    
    return ledHost(config)
    
def run(ledServer):
    ledServer.run()
    logging.info('MQTT LED Control Started')
    
   
if __name__ == '__main__':
    ledServer = setup()
    run(ledServer)
    