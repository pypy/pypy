#include "llvm/Type.h"

using namespace llvm;

TypeID  Type_getTypeID(void* T) {
    Type*   t = (Type*)T;
    return (TypeID)t->getTypeID();
}

const void* Type_getContainedType(void* T, int n) {
    Type*   t = (Type*)T;
    return t->getContainedType(n);
}

const char* Type_getDescription(void* T) {
    Type*   t = (Type*)T;
    return t->getDescription().c_str();
}
