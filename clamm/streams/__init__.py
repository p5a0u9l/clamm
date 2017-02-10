#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ Paul Adams

# built-ins
import os

# locals
from clamm.util import config

# make sure /tmp directories exist
if not os.path.exists(config["path"]["pcm"]):
    os.makedirs(config["path"]["pcm"])
if not os.path.exists(config["path"]["wav"]):
    os.makedirs(config["path"]["wav"])
if not os.path.exists(config["path"]["osa"]):
    os.makedirs(config["path"]["osa"])
