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


ExecutionEngine*    g_execution_engine;


int compile(const char* filename) {
    std::string inputfile(filename);

    //from llvm-as.cpp
    Module*     module(ParseAssemblyFile(inputfile + ".ll"));
    if (!module) {
        std::cerr << "Error: can not parse " << inputfile << ".ll\n" << std::flush;
        return false;
    }

    std::ostream *Out = new std::ofstream((inputfile + ".bc").c_str(),
            std::ios::out | std::ios::trunc | std::ios::binary);
    WriteBytecodeToFile(module, *Out); //XXX what to do with the 3rd param (NoCompress)?

    ModuleProvider* module_provider = new ExistingModuleProvider(module);
    if (!g_execution_engine) {
        g_execution_engine = ExecutionEngine::create(module_provider, false);
    } else {
        g_execution_engine->addModuleProvider(module_provider);
    }

    return true;
}


int execute(const char* funcname, int param) { //currently compiled=Module
    int err = -1;

    if (!g_execution_engine) {
        std::cerr << "Error: no llvm code compiled yet!\n" << std::flush;
        return err;
    }

    std::vector<GenericValue> args;
    args.push_back((void*)param);

    Function*   func = g_execution_engine->FindFunctionNamed(funcname);
    if (!func) {
        std::cerr << "Error: can not find function " << funcname << "\n" << std::flush;
        return err;
    }

    GenericValue gv = g_execution_engine->runFunction(func, args);
    return gv.IntVal;
}
