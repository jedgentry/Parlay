from setuptools import setup, find_packages
from distutils.extension import Extension
import os, fnmatch

RELEASE = False
USE_CYTHON = False


def find_files(directory, pattern):

    for root, dirs, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                filename = os.path.join(root, basename)
                module_name = os.path.splitext(filename)[0].replace(os.path.sep, ".")
                print "Found: " + module_name
                yield module_name, filename


ext = '*.pyx' if USE_CYTHON else '*.c'

extensions = [Extension(name, [path]) for name, path in find_files(".", ext)]

if USE_CYTHON:
    from Cython.Build import cythonize
    extensions = cythonize(extensions, gdb_debug=(not RELEASE))

setup(
    name="parlay",
    version='0.0.1',
    description="A system for building a private internet-of-things and easily talking with cyber-physical systems",
    ext_modules=extensions,
    packages=find_packages(),
    package_data={"parlay": ["parlay/ui/**/*"]},  # include ui files
    install_requires=["Twisted >14.0.0", # 13.1.0
                      "autobahn >0.9.0"] # 0.8.5
)
