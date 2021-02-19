#pragma once

#include <llvm-c/Target.h>
#include <llvm-c/Orc.h>
#include <llvm-c/Analysis.h>

LLVMBool InitializeNativeTarget(void);
