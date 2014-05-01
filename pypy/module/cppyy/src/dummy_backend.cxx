#include "cppyy.h"
#include "capi.h"

#include <map>
#include <string>
#include <sstream>
#include <utility>
#include <vector>

#include <assert.h>
#include <stdlib.h>
#include <string.h>


// add example01.cxx code
int globalAddOneToInt(int a);

namespace dummy {
#include "example01.cxx"
}

int globalAddOneToInt(int a) {
   return dummy::globalAddOneToInt(a);
}

/* pseudo-reflection data ------------------------------------------------- */
namespace {

typedef std::map<std::string, cppyy_scope_t>  Handles_t;
static Handles_t s_handles;

enum EMethodType { kNormal=0, kConstructor=1, kStatic=2 };

struct Cppyy_PseudoMethodInfo {
    Cppyy_PseudoMethodInfo(const std::string& name,
                           const std::vector<std::string>& argtypes,
                           const std::string& returntype,
                           EMethodType mtype = kNormal) :
       m_name(name), m_argtypes(argtypes), m_returntype(returntype), m_type(mtype) {}

    std::string m_name;
    std::vector<std::string> m_argtypes;
    std::string m_returntype;
    EMethodType m_type;
};

struct Cppyy_PseudoClassInfo {
    Cppyy_PseudoClassInfo() {}
    Cppyy_PseudoClassInfo(const std::vector<Cppyy_PseudoMethodInfo>& methods,
                         long method_offset) :
        m_methods(methods), m_method_offset(method_offset) {}

    std::vector<Cppyy_PseudoMethodInfo> m_methods;
    long m_method_offset;
};

typedef std::map<cppyy_scope_t, Cppyy_PseudoClassInfo> Scopes_t;
static Scopes_t s_scopes;

static std::map<std::string, long> s_methods;

struct Cppyy_InitPseudoReflectionInfo {
    Cppyy_InitPseudoReflectionInfo() {
        // class example01 --
        static long s_scope_id = 0;
        static long s_method_id = 0;

        { // class example01 --
        s_handles["example01"] = (cppyy_scope_t)++s_scope_id;

        std::vector<Cppyy_PseudoMethodInfo> methods;

        // static double staticAddToDouble(double a)
        std::vector<std::string> argtypes;
        argtypes.push_back("double");
        methods.push_back(Cppyy_PseudoMethodInfo("staticAddToDouble", argtypes, "double", kStatic));
        s_methods["static_example01::staticAddToDouble_double"] = s_method_id++;

        // static int staticAddOneToInt(int a)
        // static int staticAddOneToInt(int a, int b)
        argtypes.clear();
        argtypes.push_back("int");
        methods.push_back(Cppyy_PseudoMethodInfo("staticAddOneToInt", argtypes, "int", kStatic));
        s_methods["static_example01::staticAddOneToInt_int"] = s_method_id++;
        argtypes.push_back("int");
        methods.push_back(Cppyy_PseudoMethodInfo("staticAddOneToInt", argtypes, "int", kStatic));
        s_methods["static_example01::staticAddOneToInt_int_int"] = s_method_id++;

        // static int staticAtoi(const char* str)
        argtypes.clear();
        argtypes.push_back("const char*");
        methods.push_back(Cppyy_PseudoMethodInfo("staticAtoi", argtypes, "int", kStatic));
        s_methods["static_example01::staticAtoi_cchar*"] = s_method_id++;

        // static char* staticStrcpy(const char* strin)
        methods.push_back(Cppyy_PseudoMethodInfo("staticStrcpy", argtypes, "char*", kStatic));
        s_methods["static_example01::staticStrcpy_cchar*"] = s_method_id++;

        // static void staticSetPayload(payload* p, double d)
        // static payload* staticCyclePayload(payload* p, double d)
        // static payload staticCopyCyclePayload(payload* p, double d)
        argtypes.clear();
        argtypes.push_back("payload*");
        argtypes.push_back("double");
        methods.push_back(Cppyy_PseudoMethodInfo("staticSetPayload", argtypes, "void", kStatic));
        s_methods["static_example01::staticSetPayload_payload*_double"] = s_method_id++;
        methods.push_back(Cppyy_PseudoMethodInfo("staticCyclePayload", argtypes, "payload*", kStatic));
        s_methods["static_example01::staticCyclePayload_payload*_double"] = s_method_id++;
        methods.push_back(Cppyy_PseudoMethodInfo("staticCopyCyclePayload", argtypes, "payload", kStatic));
        s_methods["static_example01::staticCopyCyclePayload_payload*_double"] = s_method_id++;

        // static int getCount()
        // static void setCount(int)
        argtypes.clear();
        methods.push_back(Cppyy_PseudoMethodInfo("getCount", argtypes, "int", kStatic));
        s_methods["static_example01::getCount"] = s_method_id++;
        argtypes.push_back("int");
        methods.push_back(Cppyy_PseudoMethodInfo("setCount", argtypes, "void", kStatic));
        s_methods["static_example01::setCount_int"] = s_method_id++;

        // example01()
        // example01(int a)
        argtypes.clear();
        methods.push_back(Cppyy_PseudoMethodInfo("example01", argtypes, "constructor", kConstructor));
        s_methods["example01::example01"] = s_method_id++;
        argtypes.push_back("int");
        methods.push_back(Cppyy_PseudoMethodInfo("example01", argtypes, "constructor", kConstructor));
        s_methods["example01::example01_int"] = s_method_id++;

        // int addDataToInt(int a)
        argtypes.clear();
        argtypes.push_back("int");
        methods.push_back(Cppyy_PseudoMethodInfo("addDataToInt", argtypes, "int"));
        s_methods["example01::addDataToInt_int"] = s_method_id++;

        // int addDataToIntConstRef(const int& a)
        argtypes.clear();
        argtypes.push_back("const int&");
        methods.push_back(Cppyy_PseudoMethodInfo("addDataToIntConstRef", argtypes, "int"));
        s_methods["example01::addDataToIntConstRef_cint&"] = s_method_id++;

        // int overloadedAddDataToInt(int a, int b)
        argtypes.clear();
        argtypes.push_back("int");
        argtypes.push_back("int");
        methods.push_back(Cppyy_PseudoMethodInfo("overloadedAddDataToInt", argtypes, "int"));
        s_methods["example01::overloadedAddDataToInt_int_int"] = s_method_id++;

        // int overloadedAddDataToInt(int a)
        // int overloadedAddDataToInt(int a, int b, int c)
        argtypes.clear();
        argtypes.push_back("int");
        methods.push_back(Cppyy_PseudoMethodInfo("overloadedAddDataToInt", argtypes, "int"));
        s_methods["example01::overloadedAddDataToInt_int"] = s_method_id++;
        argtypes.push_back("int");
        argtypes.push_back("int");
        methods.push_back(Cppyy_PseudoMethodInfo("overloadedAddDataToInt", argtypes, "int"));
        s_methods["example01::overloadedAddDataToInt_int_int_int"] = s_method_id++;

        // double addDataToDouble(double a)
        argtypes.clear();
        argtypes.push_back("double");
        methods.push_back(Cppyy_PseudoMethodInfo("addDataToDouble", argtypes, "double"));
        s_methods["example01::addDataToDouble_double"] = s_method_id++;

        // int addDataToAtoi(const char* str)
        // char* addToStringValue(const char* str)
        argtypes.clear();
        argtypes.push_back("const char*");
        methods.push_back(Cppyy_PseudoMethodInfo("addDataToAtoi", argtypes, "int"));
        s_methods["example01::addDataToAtoi_cchar*"] = s_method_id++;
        methods.push_back(Cppyy_PseudoMethodInfo("addToStringValue", argtypes, "char*"));
        s_methods["example01::addToStringValue_cchar*"] = s_method_id++;

        // void setPayload(payload* p)
        // payload* cyclePayload(payload* p)
        // payload copyCyclePayload(payload* p)
        argtypes.clear();
        argtypes.push_back("payload*");
        methods.push_back(Cppyy_PseudoMethodInfo("setPayload", argtypes, "void"));
        s_methods["example01::setPayload_payload*"] = s_method_id++;
        methods.push_back(Cppyy_PseudoMethodInfo("cyclePayload", argtypes, "payload*"));
        s_methods["example01::cyclePayload_payload*"] = s_method_id++;
        methods.push_back(Cppyy_PseudoMethodInfo("copyCyclePayload", argtypes, "payload"));
        s_methods["example01::copyCyclePayload_payload*"] = s_method_id++;

        Cppyy_PseudoClassInfo info(methods, s_method_id - methods.size());
        s_scopes[(cppyy_scope_t)s_scope_id] = info;
        } // -- class example01

        { // class payload --
        s_handles["payload"] = (cppyy_scope_t)++s_scope_id;

        std::vector<Cppyy_PseudoMethodInfo> methods;

        // payload(double d = 0.)
        std::vector<std::string> argtypes;
        argtypes.push_back("double");
        methods.push_back(Cppyy_PseudoMethodInfo("payload", argtypes, "constructor", kConstructor));
        s_methods["payload::payload_double"] = s_method_id++;

        // double getData()
        argtypes.clear();
        methods.push_back(Cppyy_PseudoMethodInfo("getData", argtypes, "double"));
        s_methods["payload::getData"] = s_method_id++;

        // void setData(double d)
        argtypes.clear();
        argtypes.push_back("double");
        methods.push_back(Cppyy_PseudoMethodInfo("setData", argtypes, "void"));
        s_methods["payload::setData_double"] = s_method_id++;

        Cppyy_PseudoClassInfo info(methods, s_method_id - methods.size());
        s_scopes[(cppyy_scope_t)s_scope_id] = info;
        } // -- class payload
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

cppyy_type_t cppyy_actual_class(cppyy_type_t klass, cppyy_object_t /* obj */) {
    return klass;
}


/* memory management ------------------------------------------------------ */
void cppyy_destruct(cppyy_type_t handle, cppyy_object_t self) {
    if (handle == s_handles["example01"])
       delete (dummy::example01*)self;
}


/* method/function dispatching -------------------------------------------- */
void cppyy_call_v(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    switch ((long)method) {
    case 5:             //  static void example01:;staticSetPayload(payload* p, double d)
        assert(!self && nargs == 2);
        dummy::example01::staticSetPayload((dummy::payload*)(*(long*)&((CPPYY_G__value*)args)[0]),
           ((CPPYY_G__value*)args)[1].obj.d);
        break;
    case 9:             // static void example01::setCount(int)
        assert(!self && nargs == 1);
        dummy::example01::setCount(((CPPYY_G__value*)args)[0].obj.in);
        break;
    case 20:            // void example01::setPayload(payload* p);
        assert(self && nargs == 1);
        ((dummy::example01*)self)->setPayload((dummy::payload*)(*(long*)&((CPPYY_G__value*)args)[0]));
        break;
    default:
        assert(!"method unknown in cppyy_call_v");
        break;
    }
}

int cppyy_call_i(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    int result = 0;
    const long idx = (long)method;
    if (idx == s_methods["static_example01::staticAddOneToInt_int"]) {
        assert(!self && nargs == 1);
        result = dummy::example01::staticAddOneToInt(((CPPYY_G__value*)args)[0].obj.in);
    } else if (idx == s_methods["static_example01::staticAddOneToInt_int_int"]) {
        assert(!self && nargs == 2);
        result =  dummy::example01::staticAddOneToInt(
           ((CPPYY_G__value*)args)[0].obj.in, ((CPPYY_G__value*)args)[1].obj.in);
    } else if (idx == s_methods["static_example01::staticAtoi_cchar*"]) {
        assert(!self && nargs == 1);
        result = dummy::example01::staticAtoi((const char*)(*(long*)&((CPPYY_G__value*)args)[0]));
    } else if (idx == s_methods["static_example01::getCount"]) {
        assert(!self && nargs == 0);
        result = dummy::example01::getCount();
    } else if (idx == s_methods["example01::addDataToInt_int"]) {
        assert(self && nargs == 1);
        result = ((dummy::example01*)self)->addDataToInt(((CPPYY_G__value*)args)[0].obj.in);
    } else if (idx == s_methods["example01::addDataToAtoi_cchar*"]) {
        assert(self && nargs == 1);
        result = ((dummy::example01*)self)->addDataToAtoi(
           (const char*)(*(long*)&((CPPYY_G__value*)args)[0]));
    } else {
        assert(!"method unknown in cppyy_call_i");
    }
    return result;
}

long cppyy_call_l(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    long result = 0;
    const long idx = (long)method;
    if (idx == s_methods["static_example01::staticStrcpy_cchar*"]) {
        assert(!self && nargs == 1);
        result = (long)dummy::example01::staticStrcpy(
           (const char*)(*(long*)&((CPPYY_G__value*)args)[0]));
    } else if (idx == s_methods["static_example01::staticCyclePayload_payload*_double"]) {
        assert(!self && nargs == 2);
        result = (long)dummy::example01::staticCyclePayload(
           (dummy::payload*)(*(long*)&((CPPYY_G__value*)args)[0]),
           ((CPPYY_G__value*)args)[1].obj.d);
    } else if (idx == s_methods["example01::addToStringValue_cchar*"]) {
        assert(self && nargs == 1);
        result = (long)((dummy::example01*)self)->addToStringValue(
           (const char*)(*(long*)&((CPPYY_G__value*)args)[0]));
    } else if (idx == s_methods["example01::cyclePayload_payload*"]) {
        assert(self && nargs == 1);
        result = (long)((dummy::example01*)self)->cyclePayload(
           (dummy::payload*)(*(long*)&((CPPYY_G__value*)args)[0]));
    } else {
        assert(!"method unknown in cppyy_call_l");
    }
    return result;
}

double cppyy_call_d(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    double result = 0.;
    const long idx = (long)method;
    if (idx == s_methods["static_example01::staticAddToDouble_double"]) {
        assert(!self && nargs == 1);
        result = dummy::example01::staticAddToDouble(((CPPYY_G__value*)args)[0].obj.d);
    } else if (idx == s_methods["example01::addDataToDouble_double"]) {
        assert(self && nargs == 1);
        result = ((dummy::example01*)self)->addDataToDouble(((CPPYY_G__value*)args)[0].obj.d);
    } else if (idx == s_methods["payload::getData"]) {
        assert(self && nargs == 0);
        result = ((dummy::payload*)self)->getData();
    } else {
        assert(!"method unknown in cppyy_call_d");
    }
    return result;
}

char* cppyy_call_s(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    char* result = 0;
    const long idx = (long)method;
    if (idx == s_methods["static_example01::staticStrcpy_cchar*"]) {
        assert(!self && nargs == 1);
        result = dummy::example01::staticStrcpy((const char*)(*(long*)&((CPPYY_G__value*)args)[0]));
    } else {
        assert(!"method unknown in cppyy_call_s");
    }
    return result;
}

cppyy_object_t cppyy_constructor(cppyy_method_t method, cppyy_type_t handle, int nargs, void* args) {
    void* result = 0;
    const long idx = (long)method;
    if (idx == s_methods["example01::example01"]) {
        assert(nargs == 0);
        result = new dummy::example01;
    } else if (idx == s_methods["example01::example01_int"]) {
        assert(nargs == 1);
        result = new dummy::example01(((CPPYY_G__value*)args)[0].obj.in);
    } else if (idx == s_methods["payload::payload_double"]) {
        if (nargs == 0) result = new dummy::payload;
        else if (nargs == 1) result = new dummy::payload(((CPPYY_G__value*)args)[0].obj.d);
    } else {
        assert(!"method unknown in cppyy_constructor");
    }       
    return (cppyy_object_t)result;
}

cppyy_methptrgetter_t cppyy_get_methptr_getter(cppyy_type_t /* handle */, cppyy_index_t /* method_index */) {
    return (cppyy_methptrgetter_t)0;
}


/* handling of function argument buffer ----------------------------------- */
void* cppyy_allocate_function_args(size_t nargs) {
    CPPYY_G__value* args = (CPPYY_G__value*)malloc(nargs*sizeof(CPPYY_G__value));
    for (size_t i = 0; i < nargs; ++i)
        args[i].type = 'l';
    return (void*)args;
}


/* handling of function argument buffer ----------------------------------- */
void cppyy_deallocate_function_args(void* args) {
    free(args);
}

size_t cppyy_function_arg_sizeof() {
    return sizeof(CPPYY_G__value);
}

size_t cppyy_function_arg_typeoffset() {
    return offsetof(CPPYY_G__value, type);
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
    return 0;
}

int cppyy_num_bases(cppyy_type_t /*handle*/) {
   return 0;
}


/* method/function reflection information --------------------------------- */
int cppyy_num_methods(cppyy_scope_t handle) {
    return s_scopes[handle].m_methods.size();
}

cppyy_index_t cppyy_method_index_at(cppyy_scope_t /* scope */, int imeth) {
    return (cppyy_index_t)imeth;
}

char* cppyy_method_name(cppyy_scope_t handle, cppyy_index_t method_index) {
    return cppstring_to_cstring(s_scopes[handle].m_methods[(int)method_index].m_name);
}

char* cppyy_method_result_type(cppyy_scope_t handle, cppyy_index_t method_index) {
    return cppstring_to_cstring(s_scopes[handle].m_methods[method_index].m_returntype);
}
    
int cppyy_method_num_args(cppyy_scope_t handle, cppyy_index_t method_index) {
    return s_scopes[handle].m_methods[method_index].m_argtypes.size();
}

int cppyy_method_req_args(cppyy_scope_t handle, cppyy_index_t method_index) {
    return cppyy_method_num_args(handle, method_index);
}

char* cppyy_method_arg_type(cppyy_scope_t handle, cppyy_index_t method_index, int arg_index) {
    return cppstring_to_cstring(s_scopes[handle].m_methods[method_index].m_argtypes[arg_index]);
}

char* cppyy_method_arg_default(
        cppyy_scope_t /* handle */, cppyy_index_t /* method_index */, int /* arg_index */) {
    return cppstring_to_cstring("");
}

char* cppyy_method_signature(cppyy_scope_t /* handle */, cppyy_index_t /* method_index */) {
    return cppstring_to_cstring("");
}

int cppyy_method_is_template(cppyy_scope_t /* handle */, cppyy_index_t /* method_index */) {
    return 0;
}
    
cppyy_method_t cppyy_get_method(cppyy_scope_t handle, cppyy_index_t method_index) {
    if (s_scopes.find(handle) != s_scopes.end()) {
        long id = s_scopes[handle].m_method_offset + (long)method_index;
        return (cppyy_method_t)id;
    }
    assert(!"unknown class in cppyy_get_method");
    return (cppyy_method_t)0;
}


/* method properties -----------------------------------------------------  */
int cppyy_is_constructor(cppyy_type_t handle, cppyy_index_t method_index) {
    if (s_scopes.find(handle) != s_scopes.end())
        return s_scopes[handle].m_methods[method_index].m_type == kConstructor;
    assert(!"unknown class in cppyy_is_constructor");
    return 0;
}

int cppyy_is_staticmethod(cppyy_type_t handle, cppyy_index_t method_index) {
    if (s_scopes.find(handle) != s_scopes.end())
        return s_scopes[handle].m_methods[method_index].m_type == kStatic;
    assert(!"unknown class in cppyy_is_staticmethod");
    return 0;
}


/* data member reflection information ------------------------------------- */
int cppyy_num_datamembers(cppyy_scope_t /* handle */) {
    return 0;
}


/* misc helpers ----------------------------------------------------------- */
#if defined(_MSC_VER)
long long cppyy_strtoll(const char* str) {
    return _strtoi64(str, NULL, 0);
}

extern "C" unsigned long long cppyy_strtoull(const char* str) {
    return _strtoui64(str, NULL, 0);
}
#else
long long cppyy_strtoll(const char* str) {
    return strtoll(str, NULL, 0);
}

extern "C" unsigned long long cppyy_strtoull(const char* str) {
    return strtoull(str, NULL, 0);
}
#endif

void cppyy_free(void* ptr) {
    free(ptr);
}

cppyy_object_t cppyy_charp2stdstring(const char* str) {
    void* arena = new char[sizeof(std::string)];
    new (arena) std::string(str);
    return (cppyy_object_t)arena;
}

cppyy_object_t cppyy_stdstring2stdstring(cppyy_object_t ptr) {
    void* arena = new char[sizeof(std::string)];
    new (arena) std::string(*(std::string*)ptr);
    return (cppyy_object_t)arena;
}
