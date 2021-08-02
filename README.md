# CAUTION: This repository is a WORK IN PROGRESS, and may not always work as expected! 
## THESE TOOLS ARE IN VARIOUS STAGES OF DEVELOPMENT! You are welcome to submit pull requests for any improvements you make!

# About
Various tools to support high level application development at LCLS using python.  This is an effort to locate a single repo that can be referenced for developemnt. Thes are not polished tools, they still need a lot of work, so please keep that in mind.

# lcls-tools
Python tools for LCLS: 
* Device API (profile monitors, stoppers, magnets, etc...)
* SLAC Logger
* Custom Math Tools
* Image Processing Tools
* Beam calculations (emittance, solenoid alignment corrections, etc...)

# Rules of contribution (and python coding in general)
* Make your code readable (I like good one liners as much as the next person, but pulling apart syntax can be painful)
* Add comments whenever possible
* Try your best to adhere to style guidelines set forth in [PEP8](https://www.python.org/dev/peps/pep-0008/)
* Try to be [idiomatic](https://docs.python-guide.org/writing/style), there is a reason people spent time writing these guides.  
* Add tests (unittest is used currently, please use unit tests at a bare minimum)
* Focus on extensibility (don't put a bunch of modules/classes into one file or directory and make them reference each other, if you can avoid it)
* Try to understand the purpose of each tool and do not overcomplicate with business logic that can live in an application.  These should be small and useful tools/apis with well understood and firm contracts between the api and the user
* Bonus:  If you do all of the above in general, you will be a much better coder

# Python 3
Python 2 is no longer supported. Please write all new modules in Python 3.7 or above. 

# TODO
* Upgrade all master code to python 3.7 or above.
* Use mocks in unittest once we have upgraded
* Change import scheme to python3 style 
* Update style for everything python3, including asyncio, generators/yield, import changes, etc...
* Test setup.py for machine not on same network as control system and generate mock/debug objects for testing
* Actually verify a requirements.txt file covers all dependencies
* Create a CLI tool
* Provide example application using lcls_tools
* Add more examples
* Document with sphinx or mkdocs
* Make a robust and somewhat flexible logger module that knows about SLAC things, current logger is very basic

# Dependancies: See requirements.txt
