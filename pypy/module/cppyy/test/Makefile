dicts = example01Dict.so datatypesDict.so advancedcppDict.so advancedcpp2Dict.so \
overloadsDict.so stltypesDict.so operatorsDict.so fragileDict.so crossingDict.so \
std_streamsDict.so iotypesDict.so
all : $(dicts)

ifneq (${REFLEXHOME},)
  ROOTSYS := ${REFLEXHOME}
else
  ROOTSYS := ${ROOTSYS}
endif

ifeq ($(ROOTSYS),)
  genreflex=genreflex
  cppflags=-I$(shell root-config --incdir) -L$(shell root-config --libdir)
else
  genreflex=$(ROOTSYS)/bin/genreflex
  ifeq ($(wildcard $(ROOTSYS)/include),)     # standard locations used?
    cppflags=-I$(shell root-config --incdir) -L$(shell root-config --libdir)
  else
    cppflags=-I$(ROOTSYS)/include -L$(ROOTSYS)/lib64 -L$(ROOTSYS)/lib
  endif
endif

PLATFORM := $(shell uname -s)
ifeq ($(PLATFORM),Darwin)
  cppflags+=-dynamiclib -single_module -arch x86_64 -undefined dynamic_lookup
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
	echo $(cppflags)
	g++ -o $@ $^ -shared -lReflex $(cppflags) $(cppflags2)

%_rflx.cpp: %.h %.xml
	$(genreflex) $< $(genreflexflags) --selection=$*.xml --rootmap=$*Dict.rootmap --rootmap-lib=$*Dict.so
else
%Dict.so: %_cint.cxx %.cxx
	g++ -o $@ $^ -shared $(cppflags) $(cppflags2)
	rlibmap -f -o $*Dict.rootmap -l $@ -c $*_LinkDef.h

%_cint.cxx: %.h %_LinkDef.h
	rootcint -f $@ -c $*.h $*_LinkDef.h
endif

ifeq ($(CINT),)
# TODO: methptrgetter causes these tests to crash, so don't use it for now
std_streamsDict.so: std_streams.cxx std_streams.h std_streams.xml
	$(genreflex) std_streams.h --selection=std_streams.xml
	g++ -o $@ std_streams_rflx.cpp std_streams.cxx -shared -lReflex $(cppflags) $(cppflags2)
endif

.PHONY: clean
clean:
	-rm -f $(dicts) $(subst .so,.rootmap,$(dicts)) $(wildcard *_cint.h)
