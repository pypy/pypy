dicts = example01Dict.so datatypesDict.so advancedcppDict.so stltypesDict.so operatorsDict.so fragileDict.so
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

ifeq ($(shell $(genreflex) --help | grep -- --with-methptrgetter),)
  genreflexflags=
  cppflags2=-O3
else
  genreflexflags=--with-methptrgetter
  cppflags2=-Wno-pmf-conversions -O3
endif

%Dict.so: %_rflx.cpp %.cxx
	g++ -o $@ $^ -shared -lReflex $(cppflags) $(cppflags2)

%_rflx.cpp: %.h %.xml
	$(genreflex) $< $(genreflexflags) --selection=$*.xml

# rootcint -f example01_cint.cxx -c example01.h example01_LinkDef.h
# g++ -I$ROOTSYS/include example01_cint.cxx example01.cxx -shared -o example01Dict.so -L$ROOTSYS/lib -lCore -lCint
#
# rootcint -f operators_cint.cxx -c operators.h operators_LinkDef.h
# g++ -I$ROOTSYS/include operators_cint.cxx operators.cxx -shared -o operatorsDict.so -L$ROOTSYS/lib -lCore -lCint


# TODO: methptrgetter causes these tests to crash, so don't use it for now
stltypesDict.so: stltypes.cxx stltypes.h stltypes.xml
	$(genreflex) stltypes.h --selection=stltypes.xml
	g++ -o $@ stltypes_rflx.cpp stltypes.cxx -shared -lReflex $(cppflags) $(cppflags2)

operatorsDict.so: operators.cxx operators.h operators.xml
	$(genreflex) operators.h --selection=operators.xml
	g++ -o $@ operators_rflx.cpp operators.cxx -shared -lReflex $(cppflags) $(cppflags2)

.PHONY: clean
clean:
	-rm -f $(dicts)
