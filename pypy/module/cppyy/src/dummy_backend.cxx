#include "cppyy.h"
#include "capi.h"

#include <map>
#include <string>
#include <sstream>
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

struct Cppyy_PseudoMethodInfo {
    Cppyy_PseudoMethodInfo(const std::string& name,
                           const std::vector<std::string>& argtypes,
                           const std::string& returntype) :
        m_name(name), m_argtypes(argtypes), m_returntype(returntype) {}

    std::string m_name;
    std::vector<std::string> m_argtypes;
    std::string m_returntype;
};

struct Cppyy_PseudoClassInfo {
    Cppyy_PseudoClassInfo() {}
    Cppyy_PseudoClassInfo(const std::vector<Cppyy_PseudoMethodInfo>& methods) :
        m_methods(methods ) {}

    std::vector<Cppyy_PseudoMethodInfo> m_methods;
};

typedef std::map<cppyy_scope_t, Cppyy_PseudoClassInfo> Scopes_t;
static Scopes_t s_scopes;

static int example01_last_static_method = 0;
static int example01_last_constructor = 0;
static int payload_methods_offset = 0;

struct Cppyy_InitPseudoReflectionInfo {
    Cppyy_InitPseudoReflectionInfo() {
        // class example01 --
        static long s_scope_id = 0;

        { // class example01 --
        s_handles["example01"] = (cppyy_scope_t)++s_scope_id;

        std::vector<Cppyy_PseudoMethodInfo> methods;

        // ( 0) static double staticAddToDouble(double a)
        std::vector<std::string> argtypes;
        argtypes.push_back("double");
        methods.push_back(Cppyy_PseudoMethodInfo("staticAddToDouble", argtypes, "double"));

        // ( 1) static int staticAddOneToInt(int a)
        // ( 2) static int staticAddOneToInt(int a, int b)
        argtypes.clear();
        argtypes.push_back("int");
        methods.push_back(Cppyy_PseudoMethodInfo("staticAddOneToInt", argtypes, "int"));
        argtypes.push_back("int");
        methods.push_back(Cppyy_PseudoMethodInfo("staticAddOneToInt", argtypes, "int"));

        // ( 3) static int staticAtoi(const char* str)
        argtypes.clear();
        argtypes.push_back("const char*");
        methods.push_back(Cppyy_PseudoMethodInfo("staticAtoi", argtypes, "int"));

        // ( 4) static char* staticStrcpy(const char* strin)
        methods.push_back(Cppyy_PseudoMethodInfo("staticStrcpy", argtypes, "char*"));

        // ( 5) static void staticSetPayload(payload* p, double d)
        // ( 6) static payload* staticCyclePayload(payload* p, double d)
        // ( 7) static payload staticCopyCyclePayload(payload* p, double d)
        argtypes.clear();
        argtypes.push_back("payload*");
        argtypes.push_back("double");
        methods.push_back(Cppyy_PseudoMethodInfo("staticSetPayload", argtypes, "void"));
        methods.push_back(Cppyy_PseudoMethodInfo("staticCyclePayload", argtypes, "payload*"));
        methods.push_back(Cppyy_PseudoMethodInfo("staticCopyCyclePayload", argtypes, "payload"));

        // ( 8) static int getCount()
        // ( 9) static void setCount(int)
        argtypes.clear();
        methods.push_back(Cppyy_PseudoMethodInfo("getCount", argtypes, "int"));
        argtypes.push_back("int");
        methods.push_back(Cppyy_PseudoMethodInfo("setCount", argtypes, "void"));

        // cut-off is used in cppyy_is_static
        example01_last_static_method = methods.size();

        // (10) example01()
        // (11) example01(int a)
        argtypes.clear();
        methods.push_back(Cppyy_PseudoMethodInfo("example01", argtypes, "constructor"));
        argtypes.push_back("int");
        methods.push_back(Cppyy_PseudoMethodInfo("example01", argtypes, "constructor"));

        // cut-off is used in cppyy_is_constructor
        example01_last_constructor = methods.size();

        // (12) int addDataToInt(int a)
        argtypes.clear();
        argtypes.push_back("int");
        methods.push_back(Cppyy_PseudoMethodInfo("addDataToInt", argtypes, "int"));

        // (13) int addDataToIntConstRef(const int& a)
        argtypes.clear();
        argtypes.push_back("const int&");
        methods.push_back(Cppyy_PseudoMethodInfo("addDataToIntConstRef", argtypes, "int"));

        // (14) int overloadedAddDataToInt(int a, int b)
        argtypes.clear();
        argtypes.push_back("int");
        argtypes.push_back("int");
        methods.push_back(Cppyy_PseudoMethodInfo("overloadedAddDataToInt", argtypes, "int"));

        // (15) int overloadedAddDataToInt(int a)
        // (16) int overloadedAddDataToInt(int a, int b, int c)
        argtypes.clear();
        argtypes.push_back("int");
        methods.push_back(Cppyy_PseudoMethodInfo("overloadedAddDataToInt", argtypes, "int"));

        argtypes.push_back("int");
        argtypes.push_back("int");
        methods.push_back(Cppyy_PseudoMethodInfo("overloadedAddDataToInt", argtypes, "int"));

        // (17) double addDataToDouble(double a)
        argtypes.clear();
        argtypes.push_back("double");
        methods.push_back(Cppyy_PseudoMethodInfo("addDataToDouble", argtypes, "double"));

        // (18) int addDataToAtoi(const char* str)
        // (19) char* addToStringValue(const char* str)
        argtypes.clear();
        argtypes.push_back("const char*");
        methods.push_back(Cppyy_PseudoMethodInfo("addDataToAtoi", argtypes, "int"));
        methods.push_back(Cppyy_PseudoMethodInfo("addToStringValue", argtypes, "char*"));

        // (20) void setPayload(payload* p)
        // (21) payload* cyclePayload(payload* p)
        // (22) payload copyCyclePayload(payload* p)
        argtypes.clear();
        argtypes.push_back("payload*");
        methods.push_back(Cppyy_PseudoMethodInfo("setPayload", argtypes, "void"));
        methods.push_back(Cppyy_PseudoMethodInfo("cyclePayload", argtypes, "payload*"));
        methods.push_back(Cppyy_PseudoMethodInfo("copyCyclePayload", argtypes, "payload"));

        payload_methods_offset = methods.size();

        Cppyy_PseudoClassInfo info(methods);
        s_scopes[(cppyy_scope_t)s_scope_id] = info;
        } // -- class example01

        { // class payload --
        s_handles["payload"] = (cppyy_scope_t)++s_scope_id;

        std::vector<Cppyy_PseudoMethodInfo> methods;

        // (23) payload(double d = 0.)
        std::vector<std::string> argtypes;
        argtypes.push_back("double");
        methods.push_back(Cppyy_PseudoMethodInfo("payload", argtypes, "constructor"));

        // (24) double getData()
        argtypes.clear();
        methods.push_back(Cppyy_PseudoMethodInfo("getData", argtypes, "double"));

        // (25) void setData(double d)
        argtypes.clear();
        argtypes.push_back("double");
        methods.push_back(Cppyy_PseudoMethodInfo("setData", argtypes, "void"));

        Cppyy_PseudoClassInfo info(methods);
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
    switch ((long)method) {
    case 1:             // static int example01::staticAddOneToInt(int)
        assert(!self && nargs == 1);
        result = dummy::example01::staticAddOneToInt(((CPPYY_G__value*)args)[0].obj.in);
        break;
    case 2:             // static int example01::staticAddOneToInt(int, int)
        assert(!self && nargs == 2);
        result =  dummy::example01::staticAddOneToInt(
           ((CPPYY_G__value*)args)[0].obj.in, ((CPPYY_G__value*)args)[1].obj.in);
        break;
    case 3:             // static int example01::staticAtoi(const char* str)
        assert(!self && nargs == 1);
        result = dummy::example01::staticAtoi((const char*)(*(long*)&((CPPYY_G__value*)args)[0]));
        break;
    case 8:             // static int example01::getCount()
        assert(!self && nargs == 0);
        result = dummy::example01::getCount();
        break;
    case 12:            // int example01::addDataToInt(int a)
        assert(self && nargs == 1);
        result = ((dummy::example01*)self)->addDataToInt(((CPPYY_G__value*)args)[0].obj.in);
        break;
    case 18:            // int example01::addDataToAtoi(const char* str)
        assert(self && nargs == 1);
        result = ((dummy::example01*)self)->addDataToAtoi(
           (const char*)(*(long*)&((CPPYY_G__value*)args)[0]));
        break;
    default:
        assert(!"method unknown in cppyy_call_i");
        break;
    }
    return result;
}

long cppyy_call_l(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    long result = 0;
    switch ((long)method) {
    case 4:             // static char* example01::staticStrcpy(const char* strin)
        assert(!self && nargs == 1);
        result = (long)dummy::example01::staticStrcpy(
           (const char*)(*(long*)&((CPPYY_G__value*)args)[0]));
        break;
    case 6:             // static payload* example01::staticCyclePayload(payload* p, double d)
        assert(!self && nargs == 2);
        result = (long)dummy::example01::staticCyclePayload(
           (dummy::payload*)(*(long*)&((CPPYY_G__value*)args)[0]),
           ((CPPYY_G__value*)args)[1].obj.d);
        break;
    case 19:            // char* example01::addToStringValue(const char* str)
        assert(self && nargs == 1);
        result = (long)((dummy::example01*)self)->addToStringValue(
           (const char*)(*(long*)&((CPPYY_G__value*)args)[0]));
        break;
    case 21:            // payload* example01::cyclePayload(payload* p)
        assert(self && nargs == 1);
        result = (long)((dummy::example01*)self)->cyclePayload(
           (dummy::payload*)(*(long*)&((CPPYY_G__value*)args)[0]));
        break;
    default:
        assert(!"method unknown in cppyy_call_l");
        break;
    }
    return result;
}

double cppyy_call_d(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    double result = 0.;
    switch ((long)method) {
    case 0:             // static double example01::staticAddToDouble(double)
        assert(!self && nargs == 1);
        result = dummy::example01::staticAddToDouble(((CPPYY_G__value*)args)[0].obj.d);
        break;
    case 17:            // double example01::addDataToDouble(double a)
        assert(self && nargs == 1);
        result = ((dummy::example01*)self)->addDataToDouble(((CPPYY_G__value*)args)[0].obj.d);
        break;
    case 24:            // double payload::getData()
        assert(self && nargs == 0);
        result = ((dummy::payload*)self)->getData();
        break;
    default:
        assert(!"method unknown in cppyy_call_d");
        break;
    }
    return result;
}

char* cppyy_call_s(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    char* result = 0;
    switch ((long)method) {
    case 4:             // static char* example01::staticStrcpy(const char* strin)
        assert(!self && nargs == 1);
        result = dummy::example01::staticStrcpy((const char*)(*(long*)&((CPPYY_G__value*)args)[0]));
        break;
    default:
        assert(!"method unknown in cppyy_call_s");
        break;
    }
    return result;
}

cppyy_object_t cppyy_constructor(cppyy_method_t method, cppyy_type_t handle, int nargs, void* args) {
    void* result = 0;
    if (handle == s_handles["example01"]) {
        switch ((long)method) {
        case 10:
            assert(nargs == 0);
            result = new dummy::example01;
            break;
        case 11:
            assert(nargs == 1);
            result = new dummy::example01(((CPPYY_G__value*)args)[0].obj.in);
            break;
        default:
            assert(!"method of example01 unknown in cppyy_constructor");
            break;
        }
    } else if (handle == s_handles["payload"]) {
        switch ((long)method) {
        case 23:
            if (nargs == 0) result = new dummy::payload;
            else if (nargs == 1) result = new dummy::payload(((CPPYY_G__value*)args)[0].obj.d);
            break;
        default:
            assert(!"method payload unknown in cppyy_constructor");
            break;
        }
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
    if (handle == s_handles["example01"])
        return (cppyy_method_t)method_index;
    else if (handle == s_handles["payload"])
        return (cppyy_method_t)((long)method_index + payload_methods_offset);
    assert(!"unknown class in cppyy_get_method");
    return (cppyy_method_t)0;
}


/* method properties -----------------------------------------------------  */
int cppyy_is_constructor(cppyy_type_t handle, cppyy_index_t method_index) {
    if (handle == s_handles["example01"])
       return example01_last_static_method <= method_index
           && method_index < example01_last_constructor;
    else if (handle == s_handles["payload"])
       return (long)method_index == 0;
    return 0;
}

int cppyy_is_staticmethod(cppyy_type_t handle, cppyy_index_t method_index) {
    if (handle == s_handles["example01"])
        return method_index < example01_last_static_method ? 1 : 0;
    if (handle == s_handles["payload"])
        return 0;
    return 1;
}


/* data member reflection information ------------------------------------- */
int cppyy_num_datamembers(cppyy_scope_t /* handle */) {
    return 0;
}


/* misc helpers ----------------------------------------------------------- */
long long cppyy_strtoll(const char* str) {
    return strtoll(str, NULL, 0);
}

extern "C" unsigned long long cppyy_strtoull(const char* str) {
    return strtoull(str, NULL, 0);
}

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
