#include "llvm/ModuleProvider.h"

using namespace llvm;

void*   ExistingModuleProvider__init__(void* M) {
    return new ExistingModuleProvider((Module*)M);
}
