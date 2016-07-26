from setuptools import setup, find_packages
from setuptools.command.sdist import sdist
import os
import re
import fnmatch
import urllib2

UI_VERSION = "0.0.4"
UI_LOCATION = "parlay/ui/dist"


def get_version():
    VERSIONFILE = os.path.join('parlay', '__init__.py')
    initfile_lines = open(VERSIONFILE, 'rt').readlines()
    VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
    for line in initfile_lines:
        mo = re.search(VSRE, line, re.M)
        if mo:
            return mo.group(1)
    raise RuntimeError('Unable to find version string in %s.' % (VERSIONFILE,))


def find_files(directory, pattern):

    for root, dirs, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                _filename = os.path.join(root, basename)
                _modulename = os.path.splitext(_filename)[0].replace(os.path.sep, ".")
                print "Found: " + _modulename
                yield _modulename, _filename


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

here = os.path.abspath(os.path.dirname(__file__))
readme = ""
with open(os.path.join(here, 'README.md')) as f:
    readme = f.read()


def _build_docs():
    """
    Use sphinx to generate html documentation from rst doc files

    Intended for use during creation of distribution packages
    """
    import sphinx
    sphinx.build_main(['-b html', 'parlay/docs', 'parlay/docs/_build/html'])


class SDistWithDocBuild(sdist):
    def run(self):
        _build_docs()
        sdist.run(self)


setup(
    name="parlay",
    version=get_version(),
    description="A framework for developing and testing software for embedded devices",
    long_description=readme,
    author="Promenade Software, Inc.",
    author_email="info@promenadesoftware.com",
    url="https://github.com/PromenadeSoftware/Parlay",
    license="GPLv3",
    packages=find_packages(),
    package_data={"parlay": files},  # include ui files
    install_requires=["Twisted >=15.0.0",
                      "autobahn >=0.9.0",
                      "pyserial < 3.0.0"],
    extras_require={
        "secure": ["cryptography>=1.2.1", "pyOpenSSL>=0.15.1", "cffi>=1.5.0", "service-identity >=14.0.0"]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Embedded Systems',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 2.7',
    ],
    keywords='embedded device broker medical',
    zip_safe=False,
    test_suite='parlay/tests',
    cmdclass={
        'sdist': SDistWithDocBuild
    })
