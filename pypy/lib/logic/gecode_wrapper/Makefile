

CXXFLAGS=$(shell pkg-config --cflags gecode gecode-minimodel gecode-search)

LDFLAGS=$(shell pkg-config --libs gecode gecode-minimodel gecode-search)

reine: main.o libgecode_wrap.so
	gcc -o reine -L. -lgecode_wrap main.o


libgecode_wrap.so: gecode_wrap.o space_wrap.o gecode_wrap.h space_wrap.hh
	g++ -o $@ $(LDFLAGS) -shared $<


