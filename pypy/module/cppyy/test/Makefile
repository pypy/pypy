all: example01Dict.so datatypesDict.so advancedcppDict.so stltypesDict.so operatorsDict.so

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


example01Dict.so: example01.cxx example01.h example01.xml
	$(genreflex) example01.h $(genreflexflags) --selection=example01.xml
	g++ -o $@ example01_rflx.cpp example01.cxx -shared -lReflex $(cppflags) $(cppflags2)

# rootcint -f example01_cint.cxx -c example01.h
# g++ -I$ROOTSYS/include example01_cint.cxx example01.cxx -shared -o example01Dict.so -L$ROOTSYS/lib -lCore -lCint

datatypesDict.so: datatypes.cxx datatypes.h
	$(genreflex) datatypes.h $(genreflexflags)
	g++ -o $@ datatypes_rflx.cpp datatypes.cxx -shared -lReflex $(cppflags) $(cppflags2)

advancedcppDict.so: advancedcpp.cxx advancedcpp.h advancedcpp.xml
	$(genreflex) advancedcpp.h $(genreflexflags) --selection=advancedcpp.xml
	g++ -o $@ advancedcpp_rflx.cpp advancedcpp.cxx -shared -lReflex $(cppflags) $(cppflags2)

stltypesDict.so: stltypes.cxx stltypes.h stltypes.xml
	$(genreflex) stltypes.h --selection=stltypes.xml
	g++ -o $@ stltypes_rflx.cpp stltypes.cxx -shared -lReflex $(cppflags) $(cppflags2)

operatorsDict.so: operators.cxx operators.h
	$(genreflex) operators.h
	g++ -o $@ operators_rflx.cpp operators.cxx -shared -lReflex $(cppflags) $(cppflags2)
