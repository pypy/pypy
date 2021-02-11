#include "wrapper.h"

LLVMBool InitializeNativeTarget(void)	{
	return LLVMInitializeNativeTarget();
}

LLVMBool InitializeNativeAsmPrinter(void)	{
	return LLVMInitializeNativeAsmPrinter();
}

LLVMBool InitializeNativeAsmParser(void)	{
	return LLVMInitializeNativeAsmParser();
}
