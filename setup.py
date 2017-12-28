"""
setup
"""
from distutils.core import setup

setup(name='clamm',
      version='0.2.2',
      description='CLAssical Music Manager',
      author='Paul Adams',
      url='https://github.com/p5a0u9l/clamm',
      license='MIT',
      author_email='p5a0u9l@gmail.com',
      include_package_data=True,
      entry_points={
          'console_scripts': ['clamm=clamm.__main__:main']
      },
      packages=['clamm'])
