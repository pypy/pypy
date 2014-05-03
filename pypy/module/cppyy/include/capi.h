#ifndef CPPYY_CAPI
#define CPPYY_CAPI

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif // ifdef __cplusplus

    typedef long cppyy_scope_t;
    typedef cppyy_scope_t cppyy_type_t;
    typedef long cppyy_object_t;
    typedef long cppyy_method_t;
    typedef long cppyy_index_t;
    typedef void* (*cppyy_methptrgetter_t)(cppyy_object_t);

    /* name to opaque C++ scope representation -------------------------------- */
    int cppyy_num_scopes(cppyy_scope_t parent);
    char* cppyy_scope_name(cppyy_scope_t parent, int iscope);

    char* cppyy_resolve_name(const char* cppitem_name);
    cppyy_scope_t cppyy_get_scope(const char* scope_name);
    cppyy_type_t cppyy_get_template(const char* template_name);
    cppyy_type_t cppyy_actual_class(cppyy_type_t klass, cppyy_object_t obj);

    /* memory management ------------------------------------------------------ */
    cppyy_object_t cppyy_allocate(cppyy_type_t type);
    void cppyy_deallocate(cppyy_type_t type, cppyy_object_t self);
    void cppyy_destruct(cppyy_type_t type, cppyy_object_t self);

    /* method/function dispatching -------------------------------------------- */
    void   cppyy_call_v(cppyy_method_t method, cppyy_object_t self, int nargs, void* args);
    unsigned char cppyy_call_b(cppyy_method_t method, cppyy_object_t self, int nargs, void* args);
    char   cppyy_call_c(cppyy_method_t method, cppyy_object_t self, int nargs, void* args);
    short  cppyy_call_h(cppyy_method_t method, cppyy_object_t self, int nargs, void* args);
    int    cppyy_call_i(cppyy_method_t method, cppyy_object_t self, int nargs, void* args);
    long   cppyy_call_l(cppyy_method_t method, cppyy_object_t self, int nargs, void* args);
    long long cppyy_call_ll(cppyy_method_t method, cppyy_object_t self, int nargs, void* args);
    float  cppyy_call_f(cppyy_method_t method, cppyy_object_t self, int nargs, void* args);
    double cppyy_call_d(cppyy_method_t method, cppyy_object_t self, int nargs, void* args);

    void*  cppyy_call_r(cppyy_method_t method, cppyy_object_t self, int nargs, void* args);
    char*  cppyy_call_s(cppyy_method_t method, cppyy_object_t self, int nargs, void* args);

    cppyy_object_t cppyy_constructor(cppyy_method_t method, cppyy_type_t klass, int nargs, void* args);
    cppyy_object_t cppyy_call_o(cppyy_method_t method, cppyy_object_t self, int nargs, void* args, cppyy_type_t result_type);

    cppyy_methptrgetter_t cppyy_get_methptr_getter(cppyy_scope_t scope, cppyy_index_t idx);

    /* handling of function argument buffer ----------------------------------- */
    void*  cppyy_allocate_function_args(size_t nargs);
    void   cppyy_deallocate_function_args(void* args);
    size_t cppyy_function_arg_sizeof();
    size_t cppyy_function_arg_typeoffset();

    /* scope reflection information ------------------------------------------- */
    int cppyy_is_namespace(cppyy_scope_t scope);
    int cppyy_is_enum(const char* type_name);

    /* class reflection information ------------------------------------------- */
    char* cppyy_final_name(cppyy_type_t type);
    char* cppyy_scoped_final_name(cppyy_type_t type);
    int cppyy_has_complex_hierarchy(cppyy_type_t type);
    int cppyy_num_bases(cppyy_type_t type);
    char* cppyy_base_name(cppyy_type_t type, int base_index);
    int cppyy_is_subtype(cppyy_type_t derived, cppyy_type_t base);

    /* calculate offsets between declared and actual type, up-cast: direction > 0; down-cast: direction < 0 */
    size_t cppyy_base_offset(cppyy_type_t derived, cppyy_type_t base, cppyy_object_t address, int direction);

    /* method/function reflection information --------------------------------- */
    int cppyy_num_methods(cppyy_scope_t scope);
    cppyy_index_t cppyy_method_index_at(cppyy_scope_t scope, int imeth);
    cppyy_index_t* cppyy_method_indices_from_name(cppyy_scope_t scope, const char* name);

    char* cppyy_method_name(cppyy_scope_t scope, cppyy_index_t idx);
    char* cppyy_method_result_type(cppyy_scope_t scope, cppyy_index_t idx);
    int cppyy_method_num_args(cppyy_scope_t scope, cppyy_index_t idx);
    int cppyy_method_req_args(cppyy_scope_t scope, cppyy_index_t idx);
    char* cppyy_method_arg_type(cppyy_scope_t scope, cppyy_index_t idx, int arg_index);
    char* cppyy_method_arg_default(cppyy_scope_t scope, cppyy_index_t idx, int arg_index);
    char* cppyy_method_signature(cppyy_scope_t scope, cppyy_index_t idx);

    int cppyy_method_is_template(cppyy_scope_t scope, cppyy_index_t idx);
    int cppyy_method_num_template_args(cppyy_scope_t scope, cppyy_index_t idx);
    char* cppyy_method_template_arg_name(cppyy_scope_t scope, cppyy_index_t idx, cppyy_index_t iarg);

    cppyy_method_t cppyy_get_method(cppyy_scope_t scope, cppyy_index_t idx);
    cppyy_index_t cppyy_get_global_operator(
        cppyy_scope_t scope, cppyy_scope_t lc, cppyy_scope_t rc, const char* op);

    /* method properties ------------------------------------------------------ */
    int cppyy_is_constructor(cppyy_type_t type, cppyy_index_t idx);
    int cppyy_is_staticmethod(cppyy_type_t type, cppyy_index_t idx);

    /* data member reflection information ------------------------------------- */
    int cppyy_num_datamembers(cppyy_scope_t scope);
    char* cppyy_datamember_name(cppyy_scope_t scope, int datamember_index);
    char* cppyy_datamember_type(cppyy_scope_t scope, int datamember_index);
    size_t cppyy_datamember_offset(cppyy_scope_t scope, int datamember_index);

    int cppyy_datamember_index(cppyy_scope_t scope, const char* name);

    /* data member properties ------------------------------------------------- */
    int cppyy_is_publicdata(cppyy_type_t type, int datamember_index);
    int cppyy_is_staticdata(cppyy_type_t type, int datamember_index);

    /* misc helpers ----------------------------------------------------------- */
    long long cppyy_strtoll(const char* str);
    unsigned long long cppyy_strtoull(const char* str);
    void cppyy_free(void* ptr);

    cppyy_object_t cppyy_charp2stdstring(const char* str);
    cppyy_object_t cppyy_stdstring2stdstring(cppyy_object_t ptr);

#ifdef __cplusplus
}
#endif // ifdef __cplusplus

#endif // ifndef CPPYY_CAPI
