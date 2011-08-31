dicts = example01Dict.so datatypesDict.so advancedcppDict.so stltypesDict.so operatorsDict.so fragileDict.so std_streamsDict.so
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
  cppflags2=-O3 -fPIC
else
  genreflexflags=--with-methptrgetter
  cppflags2=-Wno-pmf-conversions -O3 -fPIC
endif

%Dict.so: %_rflx.cpp %.cxx
	g++ -o $@ $^ -shared -lReflex $(cppflags) $(cppflags2)

%_rflx.cpp: %.h %.xml
	$(genreflex) $< $(genreflexflags) --selection=$*.xml

# rootcint -f example01_cint.cxx -c example01.h example01_LinkDef.h
# g++ -I$ROOTSYS/include example01_cint.cxx example01.cxx -shared -o example01Dict.so -rdynamic
#
# rootcint -f operators_cint.cxx -c operators.h operators_LinkDef.h
# g++ -I$ROOTSYS/include operators_cint.cxx operators.cxx -shared -o operatorsDict.so -rdynamic
#
# rootcint -f datatypes_cint.cxx -c datatypes.h datatypes_LinkDef.h
# g++ -I$ROOTSYS/include datatypes_cint.cxx datatypes.cxx -shared -o datatypesDict.so -rdynamic
#
# rootcint -f advancedcpp_cint.cxx -c advancedcpp.h advancedcpp_LinkDef.h
# g++ -I$ROOTSYS/include advancedcpp_cint.cxx advancedcpp.cxx -shared -o advancedcppDict.so -rdynamic
#
# rootcint -f fragile_cint.cxx -c fragile.h fragile_LinkDef.h
# g++ -I$ROOTSYS/include fragile_cint.cxx fragile.cxx -shared -o fragileDict.so -rdynamic
#
# rootcint -f stltypes_cint.cxx -c stltypes.h stltypes_LinkDef.h
# g++ -I$ROOTSYS/include stltypes_cint.cxx stltypes.cxx -shared -o stltypesDict.so -rdynamic

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

.PHONY: clean
clean:
	-rm -f $(dicts)
