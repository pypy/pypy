CC=gcc
CFLAGS=$(shell llvm12-config --cflags) $(shell llvm12-config --ldflags) $(shell llvm12-config --libs) -fPIC -shared -O3 -flto -L . -lcppwrapper 

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


