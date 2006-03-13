#include <vector>
#include <iostream>
#include <stdlib.h>
#include <exception>
#include "kernel.hh"
#include "int.hh"
#include "search.hh"

#include "gecode_wrap.hh"



%(var_subclasses_body)s

%(var_factories_body)s

%(var_propagators_body)s
