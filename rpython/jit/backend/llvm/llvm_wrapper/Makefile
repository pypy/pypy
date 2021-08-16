CC=gcc
CFLAGS=$(shell llvm-config --cflags) $(shell llvm-config --ldflags) $(shell llvm-config --libs all) -fPIC -shared -O3 -flto -L . -lcppwrapper 

IDIR=.
_DEPS = wrapper.h 
DEPS=$(patsubst %,$(IDIR)/%,$(_DEPS))

all: libwrapper.so

OBJ = wrapper.o 

%.o: %.c $(DEPS)
	$(CC) -c -o $@ $< $(CFLAGS) 

libwrapper.so: $(OBJ)
	$(CC) -o $@ $^ $(CFLAGS) 

clean:
	rm -f wrapper.o libwrapper.so


