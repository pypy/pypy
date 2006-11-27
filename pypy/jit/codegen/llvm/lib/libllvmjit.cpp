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
#include "llvm/Transforms/Scalar.h"         //for createInstructionCombiningPass...

#include "llvm/Target/TargetOptions.h"      //for PrintMachineCode

#include <fstream>
#include <iostream>
#include <memory>

using namespace llvm;


Module*             gp_module           = new Module("llvmjit");
ExecutionEngine*    gp_execution_engine = ExecutionEngine::create(
                        new ExistingModuleProvider(gp_module), false);

//all optimization/transform passes
static cl::list<const PassInfo*, bool, PassNameParser>
    PassList(cl::desc("Optimizations available:"));

//some global data for the tests to play with
char    g_char[2] = {10,0};


//
//code...
//
void    restart() {
    delete gp_execution_engine; //XXX test if this correctly cleans up including generated code

    gp_module           = new Module("llvmjit");
    gp_execution_engine = ExecutionEngine::create(new ExistingModuleProvider(gp_module), false);

    //PrintMachineCode = 1;
}


int     transform(const char* passnames) {
    if (!gp_module) {
        return -1;
    }

    PassManager passes; //XXX: note: if passnames is the same as last time we can reuse passes
    passes.add(new TargetData(gp_module));

    //XXX next couple of passes should be dependent on passnames!
    passes.add(new PrintModulePass());
    passes.add(createInstructionCombiningPass());
    passes.add(createCFGSimplificationPass());
    passes.add(new PrintModulePass());
    passes.add(createVerifierPass());

    return passes.run(*gp_module);
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


char*   get_pointer_to_global_char() {
    printf("get_pointer_to_global_char g_char=%08x\n", g_char);
    return g_char;
}


void    add_global_mapping(const char* name, void* address) {
    //GlobalValue(const Type *Ty, ValueTy vty, Use *Ops, unsigned NumOps, LinkageTypes linkage, const std::string &name = "");

    /// GlobalVariable ctor - If a parent module is specified, the global is
    //  /// automatically inserted into the end of the specified modules global list.
    //    GlobalVariable(const Type *Ty, bool isConstant, LinkageTypes Linkage,
    //                     Constant *Initializer = 0, const std::string &Name = "",
    //                                      Module *Parent = 0);

    GlobalVariable  var(Type::UByteTy, false, GlobalVariable::ExternalLinkage, 0, name, gp_module);
    printf("add_global_mapping address=%08x\n", address);
    gp_execution_engine->addGlobalMapping(&var, address);
}

