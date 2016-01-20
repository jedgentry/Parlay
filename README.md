## Install Dependencies - Windows only

If you are installing Parlay on a Windows PC, you will need to install several dependencies with their own installers.  If you are on OSX or Linux, you can skip to [Install Parlay](#install-parlay) below.  

The following links will take you the download pages for each required package.  Select the appropriate installer (Python 2.7, 32- or 64-bit depending on your machine), and run each installer.  

* [Twisted](https://twistedmatrix.com/trac/wiki/Downloads#Windows)
* [zope.interface](https://pypi.python.org/pypi/zope.interface#download)


## Install Parlay

There are several methods for installing Parlay.  Unless noted, these methods work for Windows, OSX, and Linux users.  

### Install with pip

You can use python's package manager, pip, to install Parlay directly from the git repository.  

**Note**: this is NOT the way to install if you want to track the latest state of the repository.  This will only upgrade your Parlay installation when there is an official release with a new version number.  

To install directly with pip, enter the following on your command line.  

```
c:\> pip install git+ssh://git@local.promenadesoftware.com/PromenadeCommon/Parlay.git
```

_On OSX and linux, this installation method will automatically install all dependencies_.  


### Clone repository and run setup.py

Most python packages can be installed by cloning the repository (or just downloading their source), then running setup.py with the "install" command.  

```
c:\> git clone git@local.promenadesoftware.com:PromenadeCommon/Parlay.git
c:\> cd Parlay
c:\Parlay\> python setup.py install
```

To update Parlay to the latest version in the repository, just pull the latest from the repository and run setup.py again:  
```
c:\> cd Parlay
c:\Parlay\> git pull
c:\Parlay\> python setup.py install
```

_On OSX and linux, this installation method will automatically install all dependencies_.  

### Clone repository and create virtual environment

This is a more advanced method of installation.  Virtual environments allow you to isolate python applications and their dependencies.  

Read more on virtual environments [here](http://local.promenadesoftware.com:8081/PromenadeCommon/Company-Wiki/wikis/How-to-use-Python-virtual-environments). 

* Be sure virtualenv and virtualenvwrapper are installed.  See the article above for how to do this. 

* Clone the repository  
```
c:\> git clone git@local.promenadesoftware.com:PromenadeCommon/Parlay.git
```

* Create the virtual environment, and add the Parlay folder to the PYTHON_PATH with add2virtualenv  
```
c:\> mkvirtualenv parlay
(parlay) c:\> add2virtualenv Parlay
(parlay) c:\> deactivate
c:\>
```

* When the virtual environment you created is active, then the "parlay" package is available.  When you deactivate the virtual environment, the "parlay" package is no longer available.  
```
c:\> python -c "import parlay"  
   ** should see ImportError message here **
c:\> workon parlay
(parlay) c:\> python -c "import parlay"  
   ** should be no errors here **
(parlay) c:\> deactivate
c:\>
```

### Install Parlay for active development, running unit tests, etc.

# Structure and Setup for a Python Project

This document describes the standard structure for a python project here at Promenade, and also describes the setup actions needed to work with the project in the easiest way. 

This document is heavily based on [this blog post](http://blog.habnab.it/blog/2013/07/21/python-packages-and-you/). 

The goal of this structure is to enable a project to be used successfully in any of the following ways:
* within PyCharm
* from the command line
* as part of a unittest suite
* installed (via setup.py) on a user's machine


## Directory and File Structure

The files for the project should be organized as follows:

```
Project_Name
  | * Note:  This is a git repository
  | * Note:  This is NOT a python package -- no __init__.py at this level!
  |- .gitignore
  |- setup.py
  |- requirements.txt
  |- .idea/            <--- PyCharm project should be at top level, not within package
  |- package_name/
      |- __main__.py   <--- imports and calls main() function from some module if desired
      |- __init__.py
      |- subpackage1
      |   |- __init__.py
      |   |- module11.py  
      |   |- module12.py
      |   |- tests/
      |       |- __init__.py
      |       |- test_module11.py
      |       |- test_module12.py
      |
      |- subpackage2
          |- __init__.py
          |- module21.py  
          |- module22.py
          |- tests/
              |- __init__.py
              |- test_module21.py
              |- test_module22.py
```

## Code requirements

* All import statements within the package must be absolute from the root of the package, like so:
```python
# in test_module11.py above...  
from packagename.subpackage1.module11 import MyClassToTest
```  
This guarantees that all import statements will work in any of the environments we named above. It will also make hacky things like modifying sys.path unnecessary.

* All test files should be named test_*.py, and they should be contained in a tests/ sub-directory in the same directory as the modules they are testing. 

* Python code should conform to PEP 8 style guidelines, unless there is a very good reason otherwise.  PyCharm shows PEP8 compliance as you type, so just listen to it!


## Developing a project that depends on another project

When working ProjectA that depends on a package from ProjectB, it can be tricky to organize them so that import statements work in all cases.  

Here's how to do it:

* **It is not required, but easiest, if you put the two projects side-by-side within a directory:**  
```
Directory
  |- ProjectA
  |- ProjectB
```

* **Create a virtual environment for ProjectA**  
See the [python virtual environment wiki page](How-to-use-Python-virtual-environments) for detailed information on how to do this.  

* **Modify the _postactivate_ and _postdeactivate_ scripts to add ProjectB to the PYTHONPATH for the environment**  
  This allows code in ProjectA to use import modules from ProjectB, as if ProjectB were installed on your machine.  Editing these files instead of using the `add2virtualenv` command ensures that command line tools such as `coverage` or `nosetests` will have the correct PYTHONPATH defined.  
  * Change to the bin/ sub-directory of the virtual environment directory
```
(venv-projectA)$ cdvirtualenv
(venv-projectA)$ cd bin
```
  * Add the following lines to the file called _postactivate_
```
export PYTHONPATH_OLD=$PYTHONPATH
export PYTHONPATH="<full-path-to-ProjectB>"
```
  * Add the following lines to the file called _postdeactivate_
```
export PYTHONPATH=$PYTHONPATH_OLD
unset PYTHONPATH_OLD
```

* **Disallow global site packages so that virtual environment is isolated**  
```
(venv-projectA)$ toggleglobalsitepackages 
Disabled global site-packages     
```  
Make sure you see _Disabled global site-packages_ after you run the command.  Then, try to run your project and confirm that it doesn't work.  It should fail when trying to import some basic package, such as twisted.  This confirms that the project is isolated from your globally-installed packages.  

* **Install required packages in the environment**  
When the virtual environment is activated, install the requirements.txt files in both ProjectA and ProjectB to ensure you have all the required packages for both projects.  
```
(venv-projectA)$ pip install -r ProjectA/requirements.txt
(venv-projectA)$ pip install -r ProjectB/requirements.txt
```

* **In the PyCharm project for ProjectA, add the folder ProjectB as a "Content Root"**  
  * File --> Settings
  * Project: ProjectA --> Project Structure
  * Click "+ Add Content Root" on the right and select the folder ProjectB  

* **In the PyCharm project for ProjectA, add the virtual environment**  
  * File ---> Settings
  * Project: ProjectA --> Project Interpreter
  * Click the gear icon in the upper right, then "Add Local"
  * Navigate to the virtual environment directory (not the project directory), and select the Python2.7 under the bin/ directory.  
  The path is probably something like:  _/home/swdev/virtualenvs/projectA/bin/python2.7_

Now, running code from ProjectA will work in PyCharm, and on the command line!  Running unit tests and coverage with nosetests will work as well.  
 



