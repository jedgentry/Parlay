#!/bin/sh

#install requirements
pip install pyinstaller
pip install -r requirements.txt
# there is a bug with pyinstaller and setuptools after 19.2 on windows
pip install setuptools==19.2
# run installer
pyinstaller --uac-admin --onefile --icon parlay.ico --hidden-import=queue  run_parlay.py


#copy the ui
cp -rv parlay/ui dist
