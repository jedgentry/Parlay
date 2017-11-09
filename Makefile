.PHONY: clean ui test package upload release

PARLAY_UI_PATH = ../parlayui
PARLAY_UI_BUILD_PATH = $(PARLAY_UI_PATH)/build

default: 
	# do nothing by default

clean:
	rm -rf build
	rm -rf dist
	rm -rf parlay.egg-info

ui: $(PARLAY_UI_BUILD_PATH)
	rm -rf parlay/ui/dist
	mkdir -p parlay/ui/dist
	cp -r $(PARLAY_UI_BUILD_PATH)/* parlay/ui/dist

test:
	python -m unittest discover parlay/test/ -p 'test_*.py'
	python -m unittest discover parlay/test/ -p 'integration_test_*.py'

package: 
	python setup.py sdist
	python setup.py bdist_wheel

upload: 
	twine upload dist/*

release: clean ui package
	
