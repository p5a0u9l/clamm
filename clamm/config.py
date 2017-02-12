#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
import json
from os.path import join, expanduser

# bootstrap config file
cfg_path = join(expanduser('~'), '.config', 'clamm', 'config.json')
with open(cfg_path) as f:
    config = json.load(f)
