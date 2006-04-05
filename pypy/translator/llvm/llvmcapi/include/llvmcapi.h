#ifndef __LLVMCAPI_H__
#define __LLVMCAPI_H__

#ifdef __cplusplus
extern "C" {
#endif

#include "VMCore/Module.h"
#include "VMCore/ModuleProvider.h"
#include "VMCore/Function.h"
#include "VMCore/DerivedTypes.h"
#include "VMCore/Type.h"
#include "ExecutionEngine/ExecutionEngine.h"
#include "ExecutionEngine/GenericValue.h"

void    toggle_print_machineinstrs();

#ifdef __cplusplus
};
#endif

#endif
