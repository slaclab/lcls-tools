# CAUTION: This repository is a WORK IN PROGRESS! 
## THESE TOOLS ARE IN VARIOUS STAGES OF DEVELOPMENT. You are welcome to submit an issue or pull request for any improvements you would like to see or make.

# About
Various tools to support high level application development at LCLS using python.  This is an effort to maintain a single repo that can be referenced for development. 

# lcls-tools
Python tools for LCLS: 
* Device API (profile monitors, SC cavities, stoppers, magnets, etc...)
* Data processing and fitting tools
* Image collection and processing tools
* Beam calculations (emittance, solenoid alignment corrections, etc...)

# Organization
Files should be organized by their function and be as modular as possible. See [model-view-control](https://www.codecademy.com/article/mvc) programming style.
First, if the code is general enough to be used on both LCLS and LCLS-II, it belongs in the lcls-tools/common directory.
If the code specific to LCLS or LCLS-II, use the normalconducting and superconducting directories respectively.
Functions used to analyze data, belongs in the common/data_analysis directory.

# Rules of contribution 
* Try to make your code readable 
* Add comments whenever possible
* Try your best to adhere to style guidelines set forth in [PEP8](https://www.python.org/dev/peps/pep-0008/)
  * One of the automated checks for each PR is linting with flake8 and will fail otherwise.   
* Try to be [idiomatic](https://docs.python-guide.org/writing/style).
* Add tests (unittest is currently used, please use unit tests at a bare minimum)
* Focus on extensibility (don't put a bunch of modules/classes into one file or directory, if you can avoid it)
* Try to understand the purpose of each tool and do not overcomplicate with business logic that can live in an application. These should be small and useful tools/apis with well understood and firm contracts between the api and the user

# Python 3
Python 2 is no longer supported. Please write all new modules in Python 3.9 or above. 

# TODO
* See running list of to do's written up as [issues here.](https://github.com/slaclab/lcls-tools/issues)
* Provide example application using lcls_tools
* Update documentation
* Make a robust and somewhat flexible logger module that knows about SLAC things

# Dependencies and Installation

For a local development install, clone the repository and run the following commands:
```bash
pip install -e .
```

If you'd like to install the `meme` package requirement as well, run:
```bash
pip install -e ".[meme]"
```

The full list of dependencies can be found in the `requirements.txt` file.