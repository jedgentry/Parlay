
all: ui docs

ui: 
	cd parlay/ui; npm install; grunt clean; grunt build

docs: 
	cd parlay/docs; make -f Makefile html

clean:
	cd parlay/ui; grunt clean;
	cd parlay/docs; make -f Makefile clean
