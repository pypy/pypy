//implementation for using the LLVM JIT

#include "libllvmjit.h"

#include "llvm/Module.h"
#include "llvm/Assembly/Parser.h"
#include "llvm/Bytecode/Writer.h"
#include "llvm/Analysis/Verifier.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/SystemUtils.h"
#include "llvm/System/Signals.h"
#include "llvm/ModuleProvider.h"
#include "llvm/ExecutionEngine/JIT.h"
#include "llvm/ExecutionEngine/Interpreter.h"
#include "llvm/ExecutionEngine/GenericValue.h"
#include <fstream>
#include <iostream>
#include <memory>

using namespace llvm;


Module*             gp_module           = new Module("llvmjit");
ExecutionEngine*    gp_execution_engine = ExecutionEngine::create(
                        new ExistingModuleProvider(gp_module), false);


void    restart() {
    delete gp_execution_engine; //XXX test if this correctly cleans up including generated code

    gp_module           = new Module("llvmjit");
    gp_execution_engine = ExecutionEngine::create(new ExistingModuleProvider(gp_module), false);
}


int     compile(const char* llsource) {
    Module*     module = ParseAssemblyString(llsource, gp_module);
    if (!module) {
        std::cerr << "Can not parse:\n" << llsource << "\n" << std::flush;
        return false;
    }

    return true;
}


void*   find_function(const char* name) {
    return gp_execution_engine->FindFunctionNamed(name); //note: can be NULL
}


int     execute(const void* function, int param) { //XXX allow different function signatures
    if (!function) {
        std::cerr << "No function supplied to libllvmjit.execute(...)\n" << std::flush;
        return -1;
    }

    std::vector<GenericValue> args;
    args.push_back((void*)param);

    GenericValue gv = gp_execution_engine->runFunction((Function*)function, args);
    return gv.IntVal;
}

