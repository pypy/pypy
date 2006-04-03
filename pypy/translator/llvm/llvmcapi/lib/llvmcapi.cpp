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

// llvm c api includes
#include "llvmcapi.h"


using namespace llvm;


// llvm c acpi code
#include "VMCore/Module.cpp"
#include "VMCore/ModuleProvider.cpp"
#include "VMCore/Function.cpp"
#include "VMCore/DerivedTypes.cpp"
#include "ExecutionEngine/ExecutionEngine.cpp"
#include "ExecutionEngine/GenericValue.cpp"


void toggle_print_machineinstrs() {
  PrintMachineCode = !PrintMachineCode;
}
