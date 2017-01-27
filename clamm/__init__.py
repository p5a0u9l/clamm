
# built-ins
import os
import json

# globals
cfg_path = os.path.join(os.path.expanduser('~'), '.config', 'clamm', 'config.json')
with open(cfg_path) as f: config = json.load(f)

# make sure /tmp directories exist
if not os.path.exists(config["path"]["pcm"]): os.makedirs(config["path"]["pcm"])
if not os.path.exists(config["path"]["wav"]): os.makedirs(config["path"]["wav"])

