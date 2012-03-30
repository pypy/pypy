dicts = example01Dict.so datatypesDict.so advancedcppDict.so advancedcpp2Dict.so \
overloadsDict.so stltypesDict.so operatorsDict.so fragileDict.so \
std_streamsDict.so
all : $(dicts)

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

ifeq ($(CINT),)
  ifeq ($(shell $(genreflex) --help | grep -- --with-methptrgetter),)
    genreflexflags=
    cppflags2=-O3 -fPIC
  else
    genreflexflags=--with-methptrgetter
    cppflags2=-Wno-pmf-conversions -O3 -fPIC
  endif
else
  cppflags2=-O3 -fPIC -rdynamic
endif

ifeq ($(CINT),)
%Dict.so: %_rflx.cpp %.cxx
	g++ -o $@ $^ -shared -lReflex $(cppflags) $(cppflags2)

%_rflx.cpp: %.h %.xml
	$(genreflex) $< $(genreflexflags) --selection=$*.xml
else
%Dict.so: %_cint.cxx %.cxx
	g++ -o $@ $^ -shared $(cppflags) $(cppflags2)

%_cint.cxx: %.h %_LinkDef.h
	rootcint -f $@ -c $*.h $*_LinkDef.h
endif

ifeq ($(CINT),)
# TODO: methptrgetter causes these tests to crash, so don't use it for now
stltypesDict.so: stltypes.cxx stltypes.h stltypes.xml
	$(genreflex) stltypes.h --selection=stltypes.xml
	g++ -o $@ stltypes_rflx.cpp stltypes.cxx -shared -lReflex $(cppflags) $(cppflags2)

std_streamsDict.so: std_streams.cxx std_streams.h std_streams.xml
	$(genreflex) std_streams.h --selection=std_streams.xml
	g++ -o $@ std_streams_rflx.cpp std_streams.cxx -shared -lReflex $(cppflags) $(cppflags2)

operatorsDict.so: operators.cxx operators.h operators.xml
	$(genreflex) operators.h --selection=operators.xml
	g++ -o $@ operators_rflx.cpp operators.cxx -shared -lReflex $(cppflags) $(cppflags2)
endif

.PHONY: clean
clean:
	-rm -f $(dicts)
