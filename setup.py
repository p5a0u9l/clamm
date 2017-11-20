"""
setup
"""
# built-ins
from distutils.core import setup

setup(name='clamm',
      version='0.1',
      description='CLAssical Music Manager',
      author='Paul Adams',
      url='https://github.com/p5a0u9l/clamm',
      license='MIT',
      author_email='p5a0u9l@gmail.com',
      entry_points={
          'console_scripts': ['clamm=clamm.cli:main']
      },
      packages=['clamm'])
