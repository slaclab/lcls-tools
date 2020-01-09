from distutils.core import setup
import sys

if sys.version_info < (3, 6):
    error = """
lcls-tools does not support Python 2.x, 3.0, 3.1, 3.2, 3.3, 3.4, or 3.5.
Python 3.6 and above is required. Check your Python version like so:
python --version
This may be due to an out-of-date pip. Make sure you have pip >= 9.0.1.
Upgrade pip like so:
pip install --upgrade pip
"""
    sys.exit(error)


setup(
    name='lcls-tools',
    version='0.1dev',
    packages=['lcls_tools',],
    license='Apache License',
    long_description=open('README.md').read(),
)
