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
      install_requires=[
          'itunespy>=1.5.3',
          'nltk>=3.2.5',
          'translate>=3.5.0',
          'prompt-toolkit>=1.0.15',
          'wikipedia>=1.4.0',
          'colorama>=0.3.9',
          'pytaglib>=1.4.1',
          'tqdm>=4.19.5',
          'numpy>=1.13',
          'matplotlib>=2.1'
      ],
      entry_points={
          'console_scripts': ['clamm=clamm.__main__:main']
      },
      packages=['clamm'])
