dicts = advancedcppDict.so \
        advancedcpp2Dict.so \
        cpp11featuresDict.so \
        crossingDict.so \
        datatypesDict.so \
        example01Dict.so \
        fragileDict.so \
        operatorsDict.so \
        overloadsDict.so \
        stltypesDict.so \
        templatesDict.so

all : $(dicts)

HASGENREFLEX:=$(shell command -v genreflex 2> /dev/null)

cppflags=-std=c++14 -O3 -m64 -fPIC -rdynamic
ifdef HASGENREFLEX
  genreflex_flags:=$(shell genreflex --cppflags)
  cppflags+=$(genreflex_flags)
else
  cppflags+=-DCPPYY_DUMMY_BACKEND
endif

PLATFORM := $(shell uname -s)
ifeq ($(PLATFORM),Darwin)
  cppflags+=-dynamiclib -single_module -arch x86_64 -undefined dynamic_lookup
endif


ifndef HASGENREFLEX
%Dict.so: %.cxx
	$(CXX) -shared $(cppflags) -o $@ $^

else # reflex
%Dict.so: %_rflx.cpp %.cxx
	$(CXX) -shared $(cppflags) -o $@ $^

%_rflx.cpp: %.h %.xml
	genreflex $< --selection=$*.xml --rootmap=$*Dict.rootmap --rootmap-lib=$*Dict.so

endif


.PHONY: clean

clean:
	-rm -f $(dicts) $(subst .so,.rootmap,$(dicts)) $(subst Dict.so,_rflx_rdict.pcm,$(dicts)) $(subst Dict.so,_rflx.cpp,$(dicts)) $(wildcard *.pyc)
