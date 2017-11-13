#!/usr/bin/env python

# built-ins
import os
from distutils.core import setup

setup(name='clamm',
      version='0.1.1',
      description='CLAssical Music Manager',
      author='Paul Adams',
      author_email='p5a0u9l@gmail.com',
      data_files=[
          os.path.expanduser('~/.config/clamm/config.json'),
          ['json/config.json']
          ],
      entry_points={
          'console_scripts': ['clamm=clamm.clamm:main']
                      },
      packages=['clamm'])
