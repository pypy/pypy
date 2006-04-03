#include "llvm/DerivedTypes.h"

using namespace llvm;

int     FunctionType_getNumParams(void* FT) {
    FunctionType*   ft = (FunctionType*)FT;
    return ft->getNumParams();
}

const void*   FunctionType_getParamType(void* FT, int i) {
    FunctionType*   ft = (FunctionType*)FT;
    return ft->getParamType(i);
}

const void*   FunctionType_getReturnType(void* FT) {
    FunctionType*   ft = (FunctionType*)FT;
    return ft->getReturnType();
}
