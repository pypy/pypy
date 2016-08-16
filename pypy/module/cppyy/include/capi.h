#ifndef CPPYY_CAPI
#define CPPYY_CAPI

#include <stddef.h>
#include "src/precommondefs.h"

#ifdef __cplusplus
extern "C" {
#endif // ifdef __cplusplus

    typedef unsigned long cppyy_scope_t;
    typedef cppyy_scope_t cppyy_type_t;
    typedef unsigned long cppyy_object_t;
    typedef unsigned long cppyy_method_t;
    typedef long cppyy_index_t;
    typedef void* (*cppyy_methptrgetter_t)(cppyy_object_t);

    /* name to opaque C++ scope representation -------------------------------- */
    RPY_EXTERN
    int cppyy_num_scopes(cppyy_scope_t parent);
    RPY_EXTERN
    char* cppyy_scope_name(cppyy_scope_t parent, int iscope);

    RPY_EXTERN
    char* cppyy_resolve_name(const char* cppitem_name);
    RPY_EXTERN
    cppyy_scope_t cppyy_get_scope(const char* scope_name);
    RPY_EXTERN
    cppyy_type_t cppyy_actual_class(cppyy_type_t klass, cppyy_object_t obj);

    /* memory management ------------------------------------------------------ */
    RPY_EXTERN
    cppyy_object_t cppyy_allocate(cppyy_type_t type);
    RPY_EXTERN
    void cppyy_deallocate(cppyy_type_t type, cppyy_object_t self);
    RPY_EXTERN
    void cppyy_destruct(cppyy_type_t type, cppyy_object_t self);

    /* method/function dispatching -------------------------------------------- */
    RPY_EXTERN
    void   cppyy_call_v(cppyy_method_t method, cppyy_object_t self, int nargs, void* args);
    RPY_EXTERN
    unsigned char cppyy_call_b(cppyy_method_t method, cppyy_object_t self, int nargs, void* args);
    RPY_EXTERN
    char   cppyy_call_c(cppyy_method_t method, cppyy_object_t self, int nargs, void* args);
    RPY_EXTERN
    short  cppyy_call_h(cppyy_method_t method, cppyy_object_t self, int nargs, void* args);
    RPY_EXTERN
    int    cppyy_call_i(cppyy_method_t method, cppyy_object_t self, int nargs, void* args);
    RPY_EXTERN
    long   cppyy_call_l(cppyy_method_t method, cppyy_object_t self, int nargs, void* args);
    RPY_EXTERN
    long long cppyy_call_ll(cppyy_method_t method, cppyy_object_t self, int nargs, void* args);
    RPY_EXTERN
    float  cppyy_call_f(cppyy_method_t method, cppyy_object_t self, int nargs, void* args);
    RPY_EXTERN
    double cppyy_call_d(cppyy_method_t method, cppyy_object_t self, int nargs, void* args);

    RPY_EXTERN
    void*  cppyy_call_r(cppyy_method_t method, cppyy_object_t self, int nargs, void* args);
    RPY_EXTERN
    char*  cppyy_call_s(cppyy_method_t method, cppyy_object_t self, int nargs, void* args, int* length);

    RPY_EXTERN
    cppyy_object_t cppyy_constructor(cppyy_method_t method, cppyy_type_t klass, int nargs, void* args);
    RPY_EXTERN
    cppyy_object_t cppyy_call_o(cppyy_method_t method, cppyy_object_t self, int nargs, void* args, cppyy_type_t result_type);

    RPY_EXTERN
    cppyy_methptrgetter_t cppyy_get_methptr_getter(cppyy_scope_t scope, cppyy_index_t idx);

    /* handling of function argument buffer ----------------------------------- */
    RPY_EXTERN
    void*  cppyy_allocate_function_args(int nargs);
    RPY_EXTERN
    void   cppyy_deallocate_function_args(void* args);
    RPY_EXTERN
    size_t cppyy_function_arg_sizeof();
    RPY_EXTERN
    size_t cppyy_function_arg_typeoffset();

    /* scope reflection information ------------------------------------------- */
    RPY_EXTERN
    int cppyy_is_namespace(cppyy_scope_t scope);
    RPY_EXTERN
    int cppyy_is_template(const char* template_name);
    RPY_EXTERN
    int cppyy_is_abstract(cppyy_type_t type);
    RPY_EXTERN
    int cppyy_is_enum(const char* type_name);

    /* class reflection information ------------------------------------------- */
    RPY_EXTERN
    char* cppyy_final_name(cppyy_type_t type);
    RPY_EXTERN
    char* cppyy_scoped_final_name(cppyy_type_t type);
    RPY_EXTERN
    int cppyy_has_complex_hierarchy(cppyy_type_t type);
    RPY_EXTERN
    int cppyy_num_bases(cppyy_type_t type);
    RPY_EXTERN
    char* cppyy_base_name(cppyy_type_t type, int base_index);
    RPY_EXTERN
    int cppyy_is_subtype(cppyy_type_t derived, cppyy_type_t base);

    /* calculate offsets between declared and actual type, up-cast: direction > 0; down-cast: direction < 0 */
    RPY_EXTERN
    ptrdiff_t cppyy_base_offset(cppyy_type_t derived, cppyy_type_t base, cppyy_object_t address, int direction);

    /* method/function reflection information --------------------------------- */
    RPY_EXTERN
    int cppyy_num_methods(cppyy_scope_t scope);
    RPY_EXTERN
    cppyy_index_t cppyy_method_index_at(cppyy_scope_t scope, int imeth);
    RPY_EXTERN
    cppyy_index_t* cppyy_method_indices_from_name(cppyy_scope_t scope, const char* name);

    RPY_EXTERN
    char* cppyy_method_name(cppyy_scope_t scope, cppyy_index_t idx);
    RPY_EXTERN
    char* cppyy_method_result_type(cppyy_scope_t scope, cppyy_index_t idx);
    RPY_EXTERN
    int cppyy_method_num_args(cppyy_scope_t scope, cppyy_index_t idx);
    RPY_EXTERN
    int cppyy_method_req_args(cppyy_scope_t scope, cppyy_index_t idx);
    RPY_EXTERN
    char* cppyy_method_arg_type(cppyy_scope_t scope, cppyy_index_t idx, int arg_index);
    RPY_EXTERN
    char* cppyy_method_arg_default(cppyy_scope_t scope, cppyy_index_t idx, int arg_index);
    RPY_EXTERN
    char* cppyy_method_signature(cppyy_scope_t scope, cppyy_index_t idx);

    RPY_EXTERN
    int cppyy_method_is_template(cppyy_scope_t scope, cppyy_index_t idx);
    RPY_EXTERN
    int cppyy_method_num_template_args(cppyy_scope_t scope, cppyy_index_t idx);
    RPY_EXTERN
    char* cppyy_method_template_arg_name(cppyy_scope_t scope, cppyy_index_t idx, cppyy_index_t iarg);

    RPY_EXTERN
    cppyy_method_t cppyy_get_method(cppyy_scope_t scope, cppyy_index_t idx);
    RPY_EXTERN
    cppyy_index_t cppyy_get_global_operator(
        cppyy_scope_t scope, cppyy_scope_t lc, cppyy_scope_t rc, const char* op);

    /* method properties ------------------------------------------------------ */
    RPY_EXTERN
    int cppyy_is_constructor(cppyy_type_t type, cppyy_index_t idx);
    RPY_EXTERN
    int cppyy_is_staticmethod(cppyy_type_t type, cppyy_index_t idx);

    /* data member reflection information ------------------------------------- */
    RPY_EXTERN
    int cppyy_num_datamembers(cppyy_scope_t scope);
    RPY_EXTERN
    char* cppyy_datamember_name(cppyy_scope_t scope, int datamember_index);
    RPY_EXTERN
    char* cppyy_datamember_type(cppyy_scope_t scope, int datamember_index);
    RPY_EXTERN
    ptrdiff_t cppyy_datamember_offset(cppyy_scope_t scope, int datamember_index);

    RPY_EXTERN
    int cppyy_datamember_index(cppyy_scope_t scope, const char* name);

    /* data member properties ------------------------------------------------- */
    RPY_EXTERN
    int cppyy_is_publicdata(cppyy_type_t type, int datamember_index);
    RPY_EXTERN
    int cppyy_is_staticdata(cppyy_type_t type, int datamember_index);

    /* misc helpers ----------------------------------------------------------- */
    RPY_EXTERN
    long long cppyy_strtoll(const char* str);
    RPY_EXTERN
    unsigned long long cppyy_strtoull(const char* str);
    RPY_EXTERN
    void cppyy_free(void* ptr);

    RPY_EXTERN
    cppyy_object_t cppyy_charp2stdstring(const char* str, size_t sz);
    RPY_EXTERN
    cppyy_object_t cppyy_stdstring2stdstring(cppyy_object_t ptr);

#ifdef __cplusplus
}
#endif // ifdef __cplusplus

#endif // ifndef CPPYY_CAPI
