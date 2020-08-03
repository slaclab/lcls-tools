# Introduction
--------------

## About
LCLS is in need of various tools to support high level application development using python.  This is an effort to locate a single repo that can be referenced for developemnt.

-------------
## lcls-tools
Python tools for LCLS: 
* Device API (profile monitors, stoppers, magnets, etc...)
* SLAC Logger
* Custom Math Tools
* Image Processing Tools
* Beam calculations (emittance, solenoid alignment corrections, etc...)

-------------------------------------------------------
## Rules of contribution (and python coding in general)
* Make your code readable (I like good one liners as much as the next person, but pulling apart syntax can be painful)
* Add comments whenever possible
* Try your best to adhere to style guidelines set forth in [PEP8](https://www.python.org/dev/peps/pep-0008/)
* Try to be [idiomatic](https://docs.python-guide.org/writing/style), there is a reason people spent time writing these guides.  People are sick of seeing a simple operation being done a million different ways and having to parse out what insanity was behind some lines of code.
* Add tests (unittest is used currently, please use unit tests at a bare minimum)
* Focus on extensibility (don't shove a bunch of modules/classes into one file or directory and make them reference each other if you can avoid it)
* Try to understand the purpose of each tool and do not overcomplicate with business logic that can live in an application.  These should be small and useful tools/apis with well understood and firm contracts between the api and the user
* Bonus:  If you do all of the above in general, you will be a much better coder

----------------
## Why Python2.7
Unfortunately, the control system LCLS uses has Python27 as a default.  That means these tools need to be compatible.  This is a compliation of code written by different people so it's not entirely uniform, but I believe an upgrade to python 3.x will not break the world.  Speaking of that let's get to the TODO

-------
## TODO
* Upgrade to python 3.7 or above I believe will give us all the things we want.
* Use mocks in unittest once we have upgraded
* Change import scheme to python3 style (soooo much better)
* Update style for everything python3, including asyncio, generators/yield, import changes, etc...
* Test setup.py for machine not on same network as control system and generate mock/debug objects for testing
* Actually verify a requirements.txt file covers all dependencies
* Create a CLI tool
* Provide example application using lcls_tools
* Add more examples
* Document with sphinx (so boring, hoping someone else wants to do this)
* Make a robust and somewhat flexible logger module that knows about SLAC things, current logger is very basic

---------------------------------------
#### Dependancies: See requirements.txt

### CAUTION: This is a POC, use at own risk. THESE TOOLS ARE IN VARIOUS STAGES OF DEVELOPMENT
