#!/usr/bin/env python

# built-ins
import os
from distutils.core import setup

setup(name='clamm',
      version='0.1.2',
      description='CLAssical Music Manager',
      author='Paul Adams',
      url='https://github.com/p5a0u9l/clamm',
      license='MIT',
      author_email='p5a0u9l@gmail.com',
      data_files=[
          os.path.expanduser('~/.config/clamm/config.json'),
          ['json/config.json']
          ],
      entry_points={
          'console_scripts': ['clamm=clamm.clamm:main']
                      },
      packages=['clamm'])
