// sanity check
#ifndef HPY_ABI_UNIVERSAL
#  error "Internal HPy error, something is wrong with your build system. The directory hpy/forbid_python_h has been added to the include_dirs but the target ABI does not seems to be 'universal'"
#endif

#error "It is forbidden to #include <Python.h> when targeting the HPy Universal ABI"
