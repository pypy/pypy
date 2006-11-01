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


int testme(int n) {
    return n * 2;
}


void* compile(const char* filename) {
    std::string inputfile(filename);

    //from llvm-as.cpp
    Module*     module(ParseAssemblyFile(inputfile + ".ll"));
    if (!module) return NULL;

    std::ostream *Out = new std::ofstream((inputfile + ".bc").c_str(),
            std::ios::out | std::ios::trunc | std::ios::binary);
    WriteBytecodeToFile(module, *Out); //XXX what to do with the 3rd param (NoCompress)?

    return module;
}


int execute(void* compiled, const char* funcname, int param) { //currently compiled=Module
    Module* module = (Module*)compiled;
    if (!module) {
        std::cerr << "Error: can not execute " << funcname << " in a non existing module\n" << std::flush;
        return -1;
    }

    ExistingModuleProvider* module_provider = new ExistingModuleProvider(module);
    ExecutionEngine* EE = ExecutionEngine::create(module_provider, false);

    std::vector<GenericValue> args;
    args.push_back((void*)param);
    GenericValue gv = EE->runFunction(module->getNamedFunction(funcname), args);

    return gv.IntVal;
}
