#ifndef __GENERICVALUE_H__
#define __GENERICVALUE_H__

#ifdef __cplusplus
extern "C" {
#endif

//#include "llvm/ExecutionEngine/GenericValue.h"

// taken from llvm/ExecutionEngine/GenericValue.h
#define bool        signed char    // C has no boolean datatype
#define uint64_t    unsigned long long
#define int64_t     signed long long
#define PointerTy   void*

// XXX GenericValue_ grew an underscore to avoid a conflict with llvm's GenericValue
//     which has additional stuff like constructors and the like which ctypes
//     codewriter does not swallow at the moment.
//     Idealy we would rewrite/extend codewriter (
union GenericValue_ {
  bool            BoolVal;
  unsigned char   UByteVal;
  signed   char   SByteVal;
  unsigned short  UShortVal;
  signed   short  ShortVal;
  unsigned int    UIntVal;
  signed   int    IntVal;
  uint64_t        ULongVal;
  int64_t         LongVal;
  double          DoubleVal;
  float           FloatVal;
  struct { unsigned int first; unsigned int second; } UIntPairVal;
  PointerTy       PointerVal;
  unsigned char   Untyped[8];
};

void*   GenericValue__init__();

#ifdef __cplusplus
};
#endif

#endif
