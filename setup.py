from setuptools import setup, find_packages
from distutils.extension import Extension
import os
import fnmatch
import urllib2

UI_VERSION = "0.0.4"
UI_LOCATION = "parlay/ui/dist"

def find_files(directory, pattern):

    for root, dirs, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                _filename = os.path.join(root, basename)
                _modulename = os.path.splitext(_filename)[0].replace(os.path.sep, ".")
                print "Found: " + _modulename
                yield _modulename, _filename


ext = '*.c'

extensions = [Extension(name, [path]) for name, path in find_files(".", ext)]

# wget the dist file and put it in /ui/dist
if not os.path.exists(UI_LOCATION + "/index.html"):
  response = urllib2.urlopen('https://github.com/PromenadeSoftware/ParlayUI/releases/download/'+UI_VERSION+'/index.html')
  html = response.read()
  if not os.path.exists(UI_LOCATION):
      os.makedirs(UI_LOCATION)

  with open(UI_LOCATION + "/index.html", 'w+') as index_file:
      index_file.write(html)

files = [os.path.relpath(filename, "parlay")
                             for module_name, filename in find_files(UI_LOCATION, "*")]


#Custom Setup installer that will wget the UI for us
setup(
    name="parlay",
    version='0.2.0',
    description="A framework for developing and testing software for embedded devices",
    ext_modules=extensions,
    packages=find_packages(),
    package_data={"parlay": files},  # include ui files
    install_requires=["Twisted >=15.0.0",
                      "autobahn >=0.9.0",
                      "pyopenssl >=0.15.0",
                      "service-identity >=14.0.0",
                      "pyserial < 3.0.0"])
