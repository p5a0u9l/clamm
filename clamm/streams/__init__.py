import os

from clamm.util import config

# make sure /tmp directories exist
if not os.path.exists(config["path"]["pcm"]): os.makedirs(config["path"]["pcm"])
if not os.path.exists(config["path"]["wav"]): os.makedirs(config["path"]["wav"])

