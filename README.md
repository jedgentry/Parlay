dev: [![Build Status](https://travis-ci.org/PromenadeSoftware/Parlay.svg?branch=dev)](https://travis-ci.org/PromenadeSoftware/Parlay)
master: [![Build Status](https://travis-ci.org/PromenadeSoftware/Parlay.svg?branch=master)](https://travis-ci.org/PromenadeSoftware/Parlay)

![Parlay Logo](http://uploads.webflow.com/557d0c4ae62c1b7951b5d7ce/569ed5185e991d8d3ac4c5a3_Parlay%20logo.png)


# Parlay: Powerful Development and Testing System for Embedded Device Software

Parlay is software that brings visibility and accessibility to embedded devices. 

It enables:
* Comprehensive test and analysis
* Painless scientific experimentation and investigation
* Automated instrument verification with easy-to-write python scripts
* Secure remote diagnostics and data capture


## Full Documentation

The documentation for Parlay is hosted on [Read the Docs](http://parlay.readthedocs.org). 

## Installation

#### Dependencies 

Parlay requires some basic python development dependencies. Make sure these are installed
##### Linux
Run the following from a command prompt:
```
# python dependencies
sudo apt-get install python python-pip python-dev
# development dependencies
sudo apt-get install git
```

######Optional dependencies for 'secure' branch
These dependencies are only needed if you want to use the 'secure' version of Parlay that uses SSL for all websocket and http connections. 
```
sudo apt-get install libffi-dev libssl-dev
```

##### Windows

Parlay requires [PyWin32](https://sourceforge.net/projects/pywin32/files/pywin32/)  (Download the 32 bit pywin32 if your python is 32 bit, otherwise download the 64bit version)


#### Install via Python Pip

For users familiar with python, the easiest way to install Parlay is with pip:
```
c:\> pip install parlay
```

On linux you might need the sudo command :
```
~$ sudo pip install parlay
```

To install the 'secure' version of Parlay use this command

```
~$ sudo pip install git+https://github.com/PromenadeSoftware/Parlay.git#egg=parlay[secure]
```

## Examples

See the [Parlay Examples](https://github.com/PromenadeSoftware/ParlayExamples) repository. 

## Help

Check out the #parlay channel on freenode IRC for help

## License

This version of Parlay is released under the GPLv3 License. Contact [Promenade Software](http://promenadesoftware.com) for more information on a commercial license. 

## Copyright

Parlay is Copyright (C) 2015 by Promenade Software, Inc.

