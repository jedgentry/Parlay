
## Install Parlay

There are several methods for installing Parlay.  Unless noted, these methods work for Windows, OSX, and Linux users.  

### Windows only -- Install Dependencies

If you are installing Parlay on a Windows PC, you will need to install several dependencies with their own installers.  If you are on OSX or Linux, you can skip to [Install Parlay](#install-parlay) below.  

The following links will take you the download pages for each required package.  Select the appropriate installer (Python 2.7, 32- or 64-bit depending on your machine), and run each installer.  

* [Twisted](https://twistedmatrix.com/trac/wiki/Downloads#Windows)
* [zope.interface](https://pypi.python.org/pypi/zope.interface#download)


### Install with pip

You can use python's package manager, pip, to install Parlay directly from the git repository.  

**Note**: this is NOT the way to install if you want to track the latest state of the repository.  This will only upgrade your Parlay installation when there is an official release with a new version number.  

To install directly with pip, enter the following on your command line.  

```
c:\> pip install git+ssh://git@github.com/PromenadeSoftware/Parlay.git
```

_On OSX and linux, this installation method will automatically install all dependencies_.  


### Clone repository and run setup.py

Most python packages can be installed by cloning the repository (or just downloading their source), then running setup.py with the "install" command.  

```
c:\> git clone git@github.com:PromenadeSoftware/Parlay.git
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

* Be sure virtualenv and virtualenvwrapper are installed.  

* Clone the repository  
```
c:\> git clone git@github.com:PromenadeSoftware/Parlay.git
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

