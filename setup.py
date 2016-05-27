from setuptools import setup, find_packages
from distutils.extension import Extension
import os
import fnmatch

RELEASE = False
USE_CYTHON = False


def find_files(directory, pattern):

    for root, dirs, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                _filename = os.path.join(root, basename)
                _modulename = os.path.splitext(_filename)[0].replace(os.path.sep, ".")
                print "Found: " + _modulename
                yield _modulename, _filename


ext = '*.pyx' if USE_CYTHON else '*.c'

extensions = [Extension(name, [path]) for name, path in find_files(".", ext)]

if USE_CYTHON:
    from Cython.Build import cythonize
    extensions = cythonize(extensions, gdb_debug=(not RELEASE))

files = [os.path.relpath(filename, "parlay")
                             for module_name, filename in find_files("parlay/ui/dist", "*")]
# include docs
files.extend([os.path.relpath(filename, "parlay")
                             for module_name, filename in find_files("parlay/docs/_build", "*")])
setup(
    name="parlay",
    version='0.0.3',
    description="A framework for developing and testing software for embedded devices",
    ext_modules=extensions,
    packages=find_packages(),
    package_data={"parlay": files},  # include ui files
    install_requires=["Twisted >=15.0.0",
                      "autobahn >=0.9.0",
                      "pyopenssl >=0.15.0",
                      "service-identity >=14.0.0",
                      "pyserial < 3.0.0"])
