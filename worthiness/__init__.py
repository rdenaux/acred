#!/usr/bin/env python
# Copyright (c) 2019 Expert System Iberia
"""
Co-inform Worthiness checker Flask API Server
"""
import sys
import os
import re
import logging
from logging.handlers import RotatingFileHandler
import configparser
from flask import Flask


logger = logging.getLogger(__name__)

# Populated from config file
debug = 0

def override_config(cfg):
    """ Override/Add config file variables from environment
        Note: Only adds variables if [section] exists
    """
    for en, val in os.environ.items():
        logger.debug("Checking env var " + en)
        oride = re.search(r'^ACRED_([a-zA-Z]+)_(\w+)', en)
        if oride:
            section = oride.group(1)
            key = oride.group(2)
            if section in cfg:
                print('ACRED Override', section, key, val)
                cfg[section][key] = val

    return cfg


def print_config(cfg):
    strs = []
    for group in cfg:
        strs.append("[%s]" % group)
        group_cfg = cfg[group]
        for key in group_cfg:
            strs.append("\t%s=%s" % (key, group_cfg[key]))
    return "\n".join(strs)


def read_file_lines(path):
    result = []
    if not os.path.exists(path):
        logger.debug('Path %s does not point to an existing file' % path)
        return result
    with open(path, encoding='utf-8') as f:
        for line in f.readlines():
            result.append(line)
    return "\n".join(result)


# Initialize Configuration
config_file = 'acred.ini'

# Environment Override
if 'ACRED_worthinesschecker_config_file' in os.environ:
    config_file = os.environ['ACRED_worthinesschecker_config_file']

config = configparser.ConfigParser()
config.read(config_file)
print("Read config file %s as\n%s" % (config_file, print_config(config)))
#print("File contents of %s:\n%s" % (config_file, read_file_lines(config_file)))
# Override config file from environment variables
config = override_config(config)


# Check for sane config file
if 'acred' not in config:
    print("Invalid acred config file %s with value:\n\t %s" % (
        config_file, print_config(config)))
    sys.exit(1)

# Logging Configuration, default level INFO
logger = logging.getLogger('')
logger.setLevel(logging.INFO)
lformat = logging.Formatter('%(asctime)s %(name)s:%(levelname)s: %(message)s')

# Debug mode Enabled
if 'debug' in config['acredapi'] and int(config['acredapi']['debug']) != 0:
    debug = int(config['acredapi']['debug'])
    logger.setLevel(logging.DEBUG)
    logging.debug('Enabled Debug mode')

# Enable logging to file if configured
if 'logfile' in config['worthinesschecker']:
    lfh = RotatingFileHandler(config['worthinesschecker']['logfile'], maxBytes=(1048576*5), backupCount=3)
    lfh.setFormatter(lformat)
    logger.addHandler(lfh)

# STDOUT Logging defaults to Warning
if not debug:
    lsh = logging.StreamHandler(sys.stdout)
    lsh.setFormatter(lformat)
    lsh.setLevel(logging.WARNING)
    logger.addHandler(lsh)

# Create Flask APP
app = Flask(__name__)
app.config.from_object(__name__)

print('loading worthinesschecker views')
import worthiness.views
