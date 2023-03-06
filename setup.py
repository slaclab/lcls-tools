from setuptools import find_packages, setup

setup(
        name='lcls-tools',
        packages=find_packages(),
        version='0.1.dev1',
        url='https://github.com/slaclab/lcls-tools',
        license='Apache License',
        python_requires='>=3.6',
        long_description=open('README.md').read(),
        long_description_content_type='text/markdown',
        include_package_data=True,
)
