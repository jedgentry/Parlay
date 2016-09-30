#!/bin/sh

#install requirements
pip install pyinstaller
pip install -r requirements.txt

# run installer
pyinstaller --onefile --hidden-import=queue  run_parlay.py


#copy the ui
cp -rv parlay/ui dist
