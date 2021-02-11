CC=gcc
CFLAGS=$(shell llvm-config --cflags) $(shell llvm-config --ldflags) $(shell llvm-config --libs) -fPIC -shared -O2

IDIR=.
_DEPS = wrapper.h
DEPS=$(patsubst %,$(IDIR)/%,$(_DEPS))

all: libwrapper.so

wrapper.o: wrapper.c $(DEPS)
	$(CC) $(CFLAGS) -c $<

libwrapper.so: wrapper.o
	$(CC) $< $(CFLAGS) -o $@

clean:
	rm -f wrapper.o libwrapper.so

