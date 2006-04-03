#include "llvm/Function.h"

using namespace llvm;

void        Function_eraseFromParent(void* F) {
    Function*   f = (Function*)F;
    f->eraseFromParent();
}

const void* Function_getFunctionType(void* F) {
    Function*   f = (Function*)F;
    return f->getFunctionType();
}
