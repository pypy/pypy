#include "llvmcapi.h"

// llvm includes
#include "llvm/Type.h"
#include "llvm/Module.h"
#include "llvm/ModuleProvider.h"
#include "llvm/Assembly/Parser.h"
#include "llvm/Bytecode/Reader.h"
#include "llvm/ExecutionEngine/GenericValue.h"
#include "llvm/ExecutionEngine/ExecutionEngine.h"
#include "llvm/Analysis/Verifier.h"
#include "llvm/DerivedTypes.h"

#include "llvm/Support/CommandLine.h"
#include "llvm/Target/TargetOptions.h"


// c++ includes
#include <string>
#include <iostream>


int testme1(int n) {
    return n * n;
}

float testme2(float f) {
    return f * f;
}
