#!/usr/bin/env python

# built-ins
from distutils.core import setup

setup(name='clamm',
      version='0.1.1',
      description='CLAssical Music Manager',
      author='Paul Adams',
      author_email='p5a0u9l@gmail.com',
      entry_points={
          'console_scripts': ['clamm=clamm.clamm:main']
                      },
      packages=['clamm'])
