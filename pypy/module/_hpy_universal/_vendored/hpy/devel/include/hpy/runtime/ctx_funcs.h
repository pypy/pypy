#ifndef HPY_RUNTIME_CTX_FUNCS_H
#define HPY_RUNTIME_CTX_FUNCS_H

// This file contains the prototypes for all the functions defined in
// hpy/devel/src/runtime/ctx_*.c

#include "hpy.h"

// ctx_bytes.c
_HPy_HIDDEN HPy ctx_Bytes_FromStringAndSize(HPyContext *ctx, const char *v,
                                            HPy_ssize_t len);

// ctx_call.c
_HPy_HIDDEN HPy ctx_CallTupleDict(HPyContext *ctx, HPy callable, HPy args, HPy kw);
_HPy_HIDDEN HPy ctx_Call(HPyContext *ctx, HPy callable, const HPy *args, size_t nargs, HPy kwnames);
_HPy_HIDDEN HPy ctx_CallMethod(HPyContext *ctx, HPy name, const HPy *args, size_t nargs, HPy kwnames);

// ctx_err.c
_HPy_HIDDEN int ctx_Err_Occurred(HPyContext *ctx);

// ctx_listbuilder.c
_HPy_HIDDEN HPyListBuilder ctx_ListBuilder_New(HPyContext *ctx,
                                               HPy_ssize_t size);
_HPy_HIDDEN void ctx_ListBuilder_Set(HPyContext *ctx, HPyListBuilder builder,
                                     HPy_ssize_t index, HPy h_item);
_HPy_HIDDEN HPy ctx_ListBuilder_Build(HPyContext *ctx, HPyListBuilder builder);
_HPy_HIDDEN void ctx_ListBuilder_Cancel(HPyContext *ctx, HPyListBuilder builder);

// ctx_module.c
_HPy_HIDDEN HPy ctx_Module_Create(HPyContext *ctx, HPyModuleDef *hpydef);

// ctx_object.c
_HPy_HIDDEN void ctx_Dump(HPyContext *ctx, HPy h);
_HPy_HIDDEN HPy ctx_Type(HPyContext *ctx, HPy h_obj);
_HPy_HIDDEN int ctx_TypeCheck(HPyContext *ctx, HPy h_obj, HPy h_type);
_HPy_HIDDEN int ctx_Is(HPyContext *ctx, HPy h_obj, HPy h_other);
_HPy_HIDDEN HPy ctx_GetItem_i(HPyContext *ctx, HPy obj, HPy_ssize_t idx);
_HPy_HIDDEN HPy ctx_GetItem_s(HPyContext *ctx, HPy obj, const char *key);
_HPy_HIDDEN int ctx_SetItem_i(HPyContext *ctx, HPy obj, HPy_ssize_t idx, HPy value);
_HPy_HIDDEN int ctx_SetItem_s(HPyContext *ctx, HPy obj, const char *key, HPy value);
_HPy_HIDDEN int ctx_DelItem_i(HPyContext *ctx, HPy obj, HPy_ssize_t idx);
_HPy_HIDDEN int ctx_DelItem_s(HPyContext *ctx, HPy obj, const char *key);

// ctx_tracker.c
_HPy_HIDDEN HPyTracker ctx_Tracker_New(HPyContext *ctx, HPy_ssize_t size);
_HPy_HIDDEN int ctx_Tracker_Add(HPyContext *ctx, HPyTracker ht, HPy h);
_HPy_HIDDEN void ctx_Tracker_ForgetAll(HPyContext *ctx, HPyTracker ht);
_HPy_HIDDEN void ctx_Tracker_Close(HPyContext *ctx, HPyTracker ht);

// ctx_tuplebuilder.c
_HPy_HIDDEN HPyTupleBuilder ctx_TupleBuilder_New(HPyContext *ctx,
                                                 HPy_ssize_t size);
_HPy_HIDDEN void ctx_TupleBuilder_Set(HPyContext *ctx, HPyTupleBuilder builder,
                                      HPy_ssize_t index, HPy h_item);
_HPy_HIDDEN HPy ctx_TupleBuilder_Build(HPyContext *ctx, HPyTupleBuilder builder);
_HPy_HIDDEN void ctx_TupleBuilder_Cancel(HPyContext *ctx,
                                         HPyTupleBuilder builder);

// ctx_tuple.c
_HPy_HIDDEN HPy ctx_Tuple_FromArray(HPyContext *ctx, const HPy items[], HPy_ssize_t n);

// ctx_capsule.c
_HPy_HIDDEN HPy ctx_Capsule_New(HPyContext *ctx,
                                void *pointer,
                                const char *name,
                                HPyCapsule_Destructor *destructor);
_HPy_HIDDEN int ctx_Capsule_SetDestructor(HPyContext *ctx,
                                          HPy h_capsule,
                                          HPyCapsule_Destructor *destructor);

#ifndef HPY_ABI_CPYTHON
_HPy_HIDDEN void* ctx_Capsule_Get(HPyContext *ctx,
                                  HPy capsule,
                                  _HPyCapsule_key key,
                                  const char *name);
_HPy_HIDDEN int ctx_Capsule_Set(HPyContext *ctx,
                                HPy capsule,
                                _HPyCapsule_key key,
                                void *value);
#endif

// ctx_type.c
_HPy_HIDDEN void* ctx_AsStruct_Object(HPyContext *ctx, HPy h);
_HPy_HIDDEN void* ctx_AsStruct_Legacy(HPyContext *ctx, HPy h);
_HPy_HIDDEN void* ctx_AsStruct_Type(HPyContext *ctx, HPy h);
_HPy_HIDDEN void* ctx_AsStruct_Long(HPyContext *ctx, HPy h);
_HPy_HIDDEN void* ctx_AsStruct_Float(HPyContext *ctx, HPy h);
_HPy_HIDDEN void* ctx_AsStruct_Unicode(HPyContext *ctx, HPy h);
_HPy_HIDDEN void* ctx_AsStruct_Tuple(HPyContext *ctx, HPy h);
_HPy_HIDDEN void* ctx_AsStruct_List(HPyContext *ctx, HPy h);
_HPy_HIDDEN void* ctx_AsStruct_Dict(HPyContext *ctx, HPy h);
_HPy_HIDDEN void* ctx_AsStruct_Slow(HPyContext *ctx, HPy h);
_HPy_HIDDEN HPy ctx_Type_FromSpec(HPyContext *ctx, HPyType_Spec *hpyspec,
                                  HPyType_SpecParam *params);
_HPy_HIDDEN HPy ctx_New(HPyContext *ctx, HPy h_type, void **data);
_HPy_HIDDEN HPy ctx_Type_GenericNew(HPyContext *ctx, HPy h_type,
                                    const HPy *args, HPy_ssize_t nargs, HPy kw);
_HPy_HIDDEN HPyType_BuiltinShape ctx_Type_GetBuiltinShape(HPyContext *ctx,
                                                          HPy h_type);
_HPy_HIDDEN const char *ctx_Type_GetName(HPyContext *ctx, HPy type);
_HPy_HIDDEN int ctx_SetCallFunction(HPyContext *ctx, HPy h,
                                    HPyCallFunction *func);


// ctx_long.c
_HPy_HIDDEN HPy ctx_Long_FromInt32_t(HPyContext *ctx, int32_t value);
_HPy_HIDDEN HPy ctx_Long_FromUInt32_t(HPyContext *ctx, uint32_t value);
_HPy_HIDDEN HPy ctx_Long_FromInt64_t(HPyContext *ctx, int64_t v);
_HPy_HIDDEN HPy ctx_Long_FromUInt64_t(HPyContext *ctx, uint64_t v);
_HPy_HIDDEN int32_t ctx_Long_AsInt32_t(HPyContext *ctx, HPy h);
_HPy_HIDDEN uint32_t ctx_Long_AsUInt32_t(HPyContext *ctx, HPy h);
_HPy_HIDDEN uint32_t ctx_Long_AsUInt32_tMask(HPyContext *ctx, HPy h);
_HPy_HIDDEN int64_t ctx_Long_AsInt64_t(HPyContext *ctx, HPy h);
_HPy_HIDDEN uint64_t ctx_Long_AsUInt64_t(HPyContext *ctx, HPy h);
_HPy_HIDDEN uint64_t ctx_Long_AsUInt64_tMask(HPyContext *ctx, HPy h);

// ctx_eval.c
_HPy_HIDDEN HPy ctx_Compile_s(HPyContext *ctx, const char *utf8_source,
                              const char *utf8_filename, HPy_SourceKind kind);

// ctx_contextvar.c
_HPy_HIDDEN int32_t ctx_ContextVar_Get(HPyContext *ctx, HPy context_var,
                                       HPy default_value, HPy *result);
#endif /* HPY_RUNTIME_CTX_FUNCS_H */
