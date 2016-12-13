dicts = example01Dict.so datatypesDict.so advancedcppDict.so advancedcpp2Dict.so \
overloadsDict.so stltypesDict.so operatorsDict.so fragileDict.so crossingDict.so \
std_streamsDict.so iotypesDict.so
all : $(dicts)

ifneq (${REFLEXHOME},)
  ROOTSYS := ${REFLEXHOME}
else ifneq (${ROOTSYS},)
  ROOTSYS := ${ROOTSYS}
else
  DUMMY := t
endif

ifeq ($(DUMMY),t)
  cppflags=
else
  ifeq ($(ROOTSYS),)
    genreflex=genreflex
    cppflags=-pthread -std=c++11 -m64 -I./include -L./lib64 -L./lib
  else
    genreflex=$(ROOTSYS)/bin/genreflex
    cppflags=$(shell $(ROOTSYS)/bin/root-config --cflags) $(shell $(ROOTSYS)/bin/root-config --ldflags) -L$(shell $(ROOTSYS)/bin/root-config --libdir) -lCore
  endif
endif

PLATFORM := $(shell uname -s)
ifeq ($(PLATFORM),Darwin)
  cppflags+=-dynamiclib -single_module -arch x86_64 -undefined dynamic_lookup
endif

ifeq ($(DUMMY),t)
  cppflags2=-O3 -fPIC -rdynamic -std=c++11 -DCPPYY_DUMMY_BACKEND
else ifeq ($(CLING),t)
  cppflags2=-O3 -fPIC -rdynamic
else
  ifeq ($(shell $(genreflex) --help | grep -- --with-methptrgetter),)
    genreflexflags=
    cppflags2=-O3 -fPIC
  else
    genreflexflags=--with-methptrgetter
    cppflags2=-Wno-pmf-conversions -O3 -fPIC
  endif
endif

ifeq ($(CLING),t)
%Dict.so: %.h %.cxx %_cling.cxx
	g++ -o $@ $*.cxx $*_cling.cxx -shared $(cppflags) $(cppflags2)

%_cling.cxx: %.h %_LinkDef.h
	rootcling -f $@ -rml $*Dict.so -rmf $*Dict.rootmap -c $*.h $*_LinkDef.h

else ifeq ($(DUMMY),t)
%Dict.so: %.cxx
	g++ -o $@ $^ -shared $(cppflags) $(cppflags2)

else # reflex
%Dict.so: %_rflx.cpp %.cxx
	g++ -o $@ $^ -shared $(cppflags) $(cppflags2)

%_rflx.cpp: %.h %.xml
	$(genreflex) $< $(genreflexflags) --selection=$*.xml --rootmap=$*Dict.rootmap --rootmap-lib=$*Dict.so

endif

ifeq ($(DUMMY),)
# TODO: methptrgetter causes these tests to crash, so don't use it for now
std_streamsDict.so: std_streams.cxx std_streams.h std_streams.xml
	$(genreflex) std_streams.h --selection=std_streams.xml
	g++ -o $@ std_streams_rflx.cpp std_streams.cxx -shared -std=c++11 $(cppflags) $(cppflags2)
endif

.PHONY: clean
clean:
	-rm -f $(dicts) $(subst .so,.rootmap,$(dicts)) $(subst Dict.so,_rflx_rdict.pcm,$(dicts)) $(subst Dict.so,_rflx.cpp,$(dicts)) $(subst Dict.so,_cling.h,$(dicts)) $(subst Dict.so,_cling.cxx,$(dicts)) $(subst Dict.so,_cling_rdict.pcm,$(dicts)) $(wildcard *.pyc)
