from setuptools import find_packages, setup

setup(
    name='lcls-tools',
    version='0.1.dev0',
    packages=find_packages(),
    url='https://github.com/slaclab/lcls-tools',
    license='Apache License',
    python_requires='>=3.6',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    include_package_data=True,
)
