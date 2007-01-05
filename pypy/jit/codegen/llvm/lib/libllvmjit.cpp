//implementation for using the LLVM JIT

#include "libllvmjit.h"

#include "llvm/Module.h"
#include "llvm/Type.h"
#include "llvm/GlobalVariable.h"
#include "llvm/Assembly/Parser.h"
#include "llvm/Bytecode/Writer.h"
#include "llvm/Analysis/Verifier.h"
#include "llvm/Target/TargetData.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/SystemUtils.h"
#include "llvm/System/Signals.h"
#include "llvm/ModuleProvider.h"
#include "llvm/ExecutionEngine/JIT.h"
#include "llvm/ExecutionEngine/Interpreter.h"
#include "llvm/ExecutionEngine/GenericValue.h"

#include "llvm/PassManager.h"
#include "llvm/Support/PassNameParser.h"
#include "llvm/Assembly/PrintModulePass.h"  //for PrintModulePass
#include "llvm/Analysis/Verifier.h"         //for createVerifierPass
#include "llvm/Analysis/LoadValueNumbering.h" //for createLoadValueNumberingPass
#include "llvm/Transforms/Scalar.h"         //for createInstructionCombiningPass...
#include "llvm/Transforms/IPO.h"            //for createGlobalDCEPass,createIPConstantPropagationPass,createFunctionInliningPass,createConstantMergePass
#include "llvm/Target/TargetOptions.h"      //for PrintMachineCode

#include <fstream>
#include <iostream>
#include <memory>

using namespace llvm;


Module*             gp_module;
ExecutionEngine*    gp_execution_engine;

//some global data for the tests to play with
int g_data;


//
//code...
//
void    restart() {
    delete gp_execution_engine; //XXX test if this correctly cleans up including generated code

    gp_module           = new Module("llvmjit");
    if (!gp_module) {
        std::cerr << "restart() can't allocate the module\n" << std::flush;
        return;
    }

    gp_execution_engine = ExecutionEngine::create(new ExistingModuleProvider(gp_module), false);
    if (!gp_execution_engine) {
        std::cerr << "restart() can't allocate the execution engine\n" << std::flush;
        return;
    }

    //PrintMachineCode = 1;
}


int     transform(int optLevel) { //optlevel [0123]
    if (!gp_module) {
        std::cerr << "no module available for transform\n" << std::flush;
        return -1;
    }

    //XXX we should also provide transforms on function level

    //note: see llvm/projects/Stacker/lib/compiler/StackerCompiler.cpp for a good pass-list

    PassManager passes;
    passes.add(new TargetData(gp_module));           // some passes need this as a first pass
    passes.add(createVerifierPass(PrintMessageAction)); // Make sure we start with a good graph
    //passes.add(new PrintModulePass());               // Visual feedback

    if (optLevel >= 1) {
        // Clean up disgusting code
        passes.add(createCFGSimplificationPass());
        // Remove unused globals
        passes.add(createGlobalDCEPass());
        // IP Constant Propagation
        passes.add(createIPConstantPropagationPass());
        // Clean up after IPCP
        passes.add(createInstructionCombiningPass());
        // Clean up after IPCP
        passes.add(createCFGSimplificationPass());
        // Inline small definitions (functions)
        passes.add(createFunctionInliningPass());
        // Simplify cfg by copying code
        passes.add(createTailDuplicationPass());
        if (optLevel >= 2) {
            // Merge & remove BBs
            passes.add(createCFGSimplificationPass());
            // Compile silly sequences
            passes.add(createInstructionCombiningPass());
            // Reassociate expressions
            passes.add(createReassociatePass());
            // Combine silly seq's
            passes.add(createInstructionCombiningPass());
            // Eliminate tail calls
            passes.add(createTailCallEliminationPass());
            // Merge & remove BBs
            passes.add(createCFGSimplificationPass());
            // Hoist loop invariants
            passes.add(createLICMPass());
            // Clean up after the unroller
            passes.add(createInstructionCombiningPass());
            // Canonicalize indvars
            passes.add(createIndVarSimplifyPass());
            // Unroll small loops
            passes.add(createLoopUnrollPass());
            // Clean up after the unroller
            passes.add(createInstructionCombiningPass());
            // GVN for load instructions
            passes.add(createLoadValueNumberingPass());
            // Remove common subexprs
            passes.add(createGCSEPass());
            // Constant prop with SCCP
            passes.add(createSCCPPass());
        }
        if (optLevel >= 3) {
            // Run instcombine again after redundancy elimination
            passes.add(createInstructionCombiningPass());
            // Delete dead stores
            passes.add(createDeadStoreEliminationPass());
            // SSA based 'Aggressive DCE'
            passes.add(createAggressiveDCEPass());
            // Merge & remove BBs
            passes.add(createCFGSimplificationPass());
            // Merge dup global constants
            passes.add(createConstantMergePass());
        }
    }

    // Merge & remove BBs
    passes.add(createCFGSimplificationPass());
    // Memory To Register
    passes.add(createPromoteMemoryToRegisterPass());
    // Compile silly sequences
    passes.add(createInstructionCombiningPass());
    // Make sure everything is still good.
    passes.add(createVerifierPass(PrintMessageAction));
    //passes.add(new PrintModulePass());               // Visual feedback

    return passes.run(*gp_module);
}


int     parse(const char* llsource) {
    if (!gp_module) {
        restart();
    }
    if (!gp_module) {
        std::cerr << "no module available for parse\n" << std::flush;
        return false;
    }

    ParseError  parse_error;
    Module*     module = ParseAssemblyString(llsource, gp_module, &parse_error);
    if (!module) {
        int line, col;
        parse_error.getErrorLocation(line, col);
        std::cerr << "\n" << llsource << "\n" << "Error: " << parse_error.getRawMessage() << ":" << line << "," << col << "\n" << std::flush;
        return false;
    }

    return true;
}


//Function methods
void*   getPointerToFunction(const void* p_function) {
    //note: this forces JIT compilation
    return gp_execution_engine->getPointerToFunction((Function*)p_function);
}


int     freeMachineCodeForFunction(const void* p_function) {
    if (!p_function) {
        std::cerr << "No function supplied to libllvmjit.freeMachineCodeForFunction(...)\n" << std::flush;
        return 0;
    }

    gp_execution_engine->freeMachineCodeForFunction((Function*)p_function);
    return 1;
}


int     recompile(const void* function) {
    if (!function) {
        std::cerr << "No function supplied to libllvmjit.recompile(...)\n" << std::flush;
        return 0;
    }

    gp_execution_engine->recompileAndRelinkFunction((Function*)function);
    return 1;
}


int     execute(const void* function, int param) { //XXX allow different function signatures
    if (!function) {
        std::cerr << "No function supplied to libllvmjit.execute(...)\n" << std::flush;
        return -1;
    }

    std::vector<GenericValue> args;
    args.push_back((void*)param);

    GenericValue gv = gp_execution_engine->runFunction((Function*)function, args);
    //return gv.IntVal;   //llvm 1.x
    //return gv.Int32Val; //llvm 2.x
    return *(int*)&gv;  //XXX todo: figure out if there is a C define for the llvm version
}


//code for testcases
int     get_global_data() {
    return g_data;
}


void    set_global_data(int n) {
    g_data = n;
}


int*   get_pointer_to_global_data() {
    return &g_data;
}


int     global_function(int a, int b, int c) {
    return a + b + c;
}


void*   get_pointer_to_global_function() {
    return (void*)global_function; //note: we don't care about the actual signature here
}


// Module methods
void*   getNamedFunction(const char* name) {
    if (!gp_module) {
        std::cerr << "no module available for getNamedFunction\n" << std::flush;
        return NULL;
    }

    return gp_module->getNamedFunction(name); //note: can be NULL
}


void*   getNamedGlobal(const char* name) {
    return gp_module->getNamedGlobal(name); //note: can be NULL
}


void    addGlobalMapping(const void* p, void* address) {
    if (!p) {
        std::cerr << "No global variable or function supplied to addGlobalMapping\n" << std::flush;
        return;
    }
    gp_execution_engine->addGlobalMapping((const GlobalValue*)p, address);
}

