
# locals
from . import library
from . import streams

# built-ins
import json

# globals
with open("config.json") as f: config = json.load(f)
