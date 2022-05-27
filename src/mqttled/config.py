#!/usr/bin/env python3

import os
import sys
import logging
import yaml
from schema import Schema, And, Or, Use, Optional, SchemaError
import jsonpath_ng
from uci import Uci

def json_path(txt):
    try:
        return jsonpath_ng.parse(txt)
    except Exception as e:
        raise SchemaError('Bad JsonPath format: %s' % txt)


def str_or_jsonPath(txt):
    if "$." in txt:
        return json_path(txt)
    return txt


def port_range(port):
    return 0 <= port <= 65535


schema = Schema({
    'mqtt': {
        'host': And(str, len),
        'port': And(int, port_range),
        'interface': And(str, len),
        Optional('username'): And(str, len),
        Optional('password'): And(str, len),
        Optional('cafile'): os.path.exists,
        Optional('certfile'): os.path.exists,
        Optional('keyfile'): os.path.exists,
        Optional('discovery'): And(str, len),
        Optional('basetopic'): And(str, len),
        Optional('subtopic'): And(str, len),
        Optional('model'): And(str, len)
    },
    'leds' : {
        Optional('all', default=True): (bool),
        Optional('include', default = []): (list),
        Optional('exclude', default = []): (list)
    },
    Optional('triggers'): (list),
    Optional("base64decode"): {
        'source': And(str, len, Use(str_or_jsonPath)),
        'target': And(str, len)
    },
})


def load_yaml(config_filename):
    with open(config_filename, 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
        try:
            return schema.validate(config)
        except SchemaError as e:
            # Better error format
            error = str(e).splitlines()
            del error[1]
            raise Exception(' '.join(error))
        
def load_uci(configpath='mqttled'):
    u = Uci()
    try:
        config = u.get(configpath)
    except UciExceptionNotFound as e:
        error = str(e).splitlines()
        raise Exception(' '.join(error))
    return config
    