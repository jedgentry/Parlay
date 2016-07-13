
all: docs

docs: 
	cd parlay/docs; make -f Makefile html

clean:
	cd parlay/docs; make -f Makefile clean
