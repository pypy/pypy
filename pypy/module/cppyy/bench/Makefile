all: bench02Dict_reflex.so

ROOTSYS := ${ROOTSYS}

ifeq ($(ROOTSYS),)
  genreflex=genreflex
  cppflags=
else
  genreflex=$(ROOTSYS)/bin/genreflex
  cppflags=-I$(ROOTSYS)/include -L$(ROOTSYS)/lib
endif

PLATFORM := $(shell uname -s)
ifeq ($(PLATFORM),Darwin)
  cppflags+=-dynamiclib -single_module -arch x86_64
endif

ifeq ($(shell $(genreflex) --help | grep -- --with-methptrgetter),)
  genreflexflags=
  cppflags2=-O3
else
  genreflexflags=--with-methptrgetter
  cppflags2=-Wno-pmf-conversions -O3
endif


bench02Dict_reflex.so: bench02.h bench02.xml
	$(genreflex) bench02.h $(genreflexflags) --selection=bench02.xml -I$(ROOTSYS)/include
	g++ -o $@ bench02.cxx bench02_rflx.cpp -I$(ROOTSYS)/include -shared -lReflex `root-config --libs` $(cppflags) $(cppflags2)
