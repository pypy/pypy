#include "cppyy.h"
#include "capi.h"

#include <map>
#include <string>
#include <vector>

#include <stdlib.h>
#include <string.h>


/* pseudo-reflection data ------------------------------------------------- */
namespace {

typedef std::map<std::string, cppyy_scope_t>  Handles_t;
static Handles_t s_handles;

class Cppyy_PseudoInfo {
public:
    Cppyy_PseudoInfo(int num_methods=0, const char* methods[]=0) :
            m_num_methods(num_methods) {
       m_methods.reserve(num_methods);
       for (int i=0; i < num_methods; ++i) {
           m_methods.push_back(methods[i]);
       } 
    }

public:
    int m_num_methods;
    std::vector<std::string> m_methods;
};

typedef std::map<cppyy_scope_t, Cppyy_PseudoInfo> Scopes_t;
static Scopes_t s_scopes;

struct Cppyy_InitPseudoReflectionInfo {
    Cppyy_InitPseudoReflectionInfo() {
        // class example01 --
        static long s_scope_id = 0;
        s_handles["example01"] = (cppyy_scope_t)++s_scope_id;
        const char* methods[] = {"staticAddToDouble"};
        Cppyy_PseudoInfo info(1, methods);
        s_scopes[(cppyy_scope_t)s_scope_id] = info;
        // -- class example01
    }
} _init;

} // unnamed namespace


/* local helpers ---------------------------------------------------------- */
static inline char* cppstring_to_cstring(const std::string& name) {
    char* name_char = (char*)malloc(name.size() + 1);
    strcpy(name_char, name.c_str());
    return name_char;
}


/* name to opaque C++ scope representation -------------------------------- */
int cppyy_num_scopes(cppyy_scope_t handle) {
    return 0;
}

char* cppyy_resolve_name(const char* cppitem_name) {
    return cppstring_to_cstring(cppitem_name);
}

cppyy_scope_t cppyy_get_scope(const char* scope_name) {
    return s_handles[scope_name];  // lookup failure will return 0 (== error)
}


/* method/function dispatching -------------------------------------------- */
cppyy_methptrgetter_t cppyy_get_methptr_getter(cppyy_type_t /* handle */, cppyy_index_t /* method_index */) {
    return (cppyy_methptrgetter_t)0;
}


/* scope reflection information ------------------------------------------- */
int cppyy_is_namespace(cppyy_scope_t /* handle */) {
    return 0;
}   

int cppyy_is_enum(const char* /* type_name */) {
    return 0;
}
    
    
/* class reflection information ------------------------------------------- */
char* cppyy_final_name(cppyy_type_t handle) {
    for (Handles_t::iterator isp = s_handles.begin(); isp != s_handles.end(); ++isp) {
        if (isp->second == handle)
            return cppstring_to_cstring(isp->first);
    }
    return cppstring_to_cstring("<unknown>");
}

char* cppyy_scoped_final_name(cppyy_type_t handle) {
    return cppyy_final_name(handle);
}   

int cppyy_has_complex_hierarchy(cppyy_type_t /* handle */) {
    return 1;
}


/* method/function reflection information --------------------------------- */
int cppyy_num_methods(cppyy_scope_t handle) {
    return s_scopes[handle].m_num_methods;
}

cppyy_index_t cppyy_method_index_at(cppyy_scope_t /* scope */, int imeth) {
    return (cppyy_index_t)imeth;
}

char* cppyy_method_name(cppyy_scope_t handle, cppyy_index_t method_index) {
    return cppstring_to_cstring(s_scopes[handle].m_methods[(int)method_index]);
}

char* cppyy_method_result_type(cppyy_scope_t /* handle */, cppyy_index_t /* method_index */) {
    return cppstring_to_cstring("double");
}
    
int cppyy_method_num_args(cppyy_scope_t /* handle */, cppyy_index_t /* method_index */) {
    return 1;
}

int cppyy_method_req_args(cppyy_scope_t handle, cppyy_index_t method_index) {
    return cppyy_method_num_args(handle, method_index);
}

char* cppyy_method_arg_type(cppyy_scope_t /* handle */, cppyy_index_t /* method_index */, int /* arg_index */) {
    return cppstring_to_cstring("double");
}

char* cppyy_method_arg_default(cppyy_scope_t handle, cppyy_index_t method_index, int arg_index) {
    return cppstring_to_cstring("");
}

char* cppyy_method_signature(cppyy_scope_t /* handle */, cppyy_index_t /* method_index */) {
    return cppstring_to_cstring("double");
}

int cppyy_method_is_template(cppyy_scope_t /* handle */, cppyy_index_t /* method_index */) {
    return 0;
}
    
cppyy_method_t cppyy_get_method(cppyy_scope_t /* handle */, cppyy_index_t method_index) {
    return (cppyy_method_t)method_index;
}


/* method properties -----------------------------------------------------  */
int cppyy_is_constructor(cppyy_type_t /* handle */, cppyy_index_t /* method_index */) {
    return 0;
}

int cppyy_is_staticmethod(cppyy_type_t /* handle */, cppyy_index_t /* method_index */) {
    return 1;
}


/* data member reflection information ------------------------------------- */
int cppyy_num_datamembers(cppyy_scope_t /* handle */) {
    return 0;
}


/* misc helpers ----------------------------------------------------------- */
void cppyy_free(void* ptr) {
    free(ptr);
}
