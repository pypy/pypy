#include "cppyy.h"
#include "capi.h"

#include <map>
#include <string>
#include <sstream>
#include <utility>
#include <vector>

#include <assert.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#pragma GCC diagnostic ignored "-Winvalid-offsetof"

// add example01.cxx code
int globalAddOneToInt(int a);

namespace dummy {
#include "example01.cxx"
#include "datatypes.cxx"
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

struct Cppyy_PseudoDatambrInfo {
    Cppyy_PseudoDatambrInfo(const std::string& name,
                            const std::string& type,
                            ptrdiff_t offset, bool isstatic) :
        m_name(name), m_type(type), m_offset(offset), m_isstatic(isstatic) {}

    std::string m_name;
    std::string m_type;
    ptrdiff_t m_offset;
    bool m_isstatic;
};

struct Cppyy_PseudoClassInfo {
    Cppyy_PseudoClassInfo() {}
    Cppyy_PseudoClassInfo(const std::vector<Cppyy_PseudoMethodInfo>& methods,
                          long method_offset,
                          const std::vector<Cppyy_PseudoDatambrInfo>& data) :
        m_methods(methods), m_method_offset(method_offset), m_datambrs(data) {}

    std::vector<Cppyy_PseudoMethodInfo> m_methods;
    long m_method_offset;
    std::vector<Cppyy_PseudoDatambrInfo> m_datambrs;
};

typedef std::map<cppyy_scope_t, Cppyy_PseudoClassInfo> Scopes_t;
static Scopes_t s_scopes;

static std::map<std::string, long> s_methods;

#define PUBLIC_CPPYY_DATA(dmname, dmtype)                                     \
    data.push_back(Cppyy_PseudoDatambrInfo("m_"#dmname, #dmtype,              \
        offsetof(dummy::cppyy_test_data, m_##dmname), false));                \
    argtypes.clear();                                                         \
    methods.push_back(Cppyy_PseudoMethodInfo(                                 \
                         "get_"#dmname, argtypes, #dmtype));                  \
    s_methods["cppyy_test_data::get_"#dmname] = s_method_id++;                \
    argtypes.push_back(#dmtype);                                              \
    methods.push_back(Cppyy_PseudoMethodInfo(                                 \
                         "set_"#dmname, argtypes, "void"));                   \
    s_methods["cppyy_test_data::set_"#dmname] = s_method_id++;                \
    argtypes.clear();                                                         \
    argtypes.push_back("const "#dmtype"&");                                   \
    methods.push_back(Cppyy_PseudoMethodInfo(                                 \
                         "set_"#dmname"_c", argtypes, "void"));               \
    s_methods["cppyy_test_data::set_"#dmname"_c"] = s_method_id++

#define PUBLIC_CPPYY_DATA2(dmname, dmtype)                                    \
    PUBLIC_CPPYY_DATA(dmname, dmtype);                                        \
    data.push_back(Cppyy_PseudoDatambrInfo("m_"#dmname"_array", #dmtype"[5]", \
        offsetof(dummy::cppyy_test_data, m_##dmname##_array), false));        \
    data.push_back(Cppyy_PseudoDatambrInfo("m_"#dmname"_array2", #dmtype"*",  \
        offsetof(dummy::cppyy_test_data, m_##dmname##_array2), false));       \
    argtypes.clear();                                                         \
    methods.push_back(Cppyy_PseudoMethodInfo(                                 \
                         "get_"#dmname"_array", argtypes, #dmtype"*"));       \
    s_methods["cppyy_test_data::get_"#dmname"_array"] = s_method_id++;        \
    methods.push_back(Cppyy_PseudoMethodInfo(                                 \
                         "get_"#dmname"_array2", argtypes, #dmtype"*"));      \
    s_methods["cppyy_test_data::get_"#dmname"_array2"] = s_method_id++

#define PUBLIC_CPPYY_DATA3(dmname, dmtype, key)                               \
    PUBLIC_CPPYY_DATA2(dmname, dmtype);                                       \
    argtypes.push_back(#dmtype"*");                                           \
    methods.push_back(Cppyy_PseudoMethodInfo(                                 \
                         "pass_array", argtypes, #dmtype"*"));                \
    s_methods["cppyy_test_data::pass_array_"#dmname] = s_method_id++;         \
    argtypes.clear(); argtypes.push_back("void*");                            \
    methods.push_back(Cppyy_PseudoMethodInfo(                                 \
                         "pass_void_array_"#key, argtypes, #dmtype"*"));      \
    s_methods["cppyy_test_data::pass_void_array_"#key] = s_method_id++

#define PUBLIC_CPPYY_STATIC_DATA(dmname, dmtype)                              \
    data.push_back(Cppyy_PseudoDatambrInfo("s_"#dmname, #dmtype,              \
        (ptrdiff_t)&dummy::cppyy_test_data::s_##dmname, true))


struct Cppyy_InitPseudoReflectionInfo {
    Cppyy_InitPseudoReflectionInfo() {
        // class example01 --
        static long s_scope_id  = 0;
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

        Cppyy_PseudoClassInfo info(
            methods, s_method_id - methods.size(), std::vector<Cppyy_PseudoDatambrInfo>());
        s_scopes[(cppyy_scope_t)s_scope_id] = info;
        } // -- class example01

        //====================================================================

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

        Cppyy_PseudoClassInfo info(
            methods, s_method_id - methods.size(), std::vector<Cppyy_PseudoDatambrInfo>());
        s_scopes[(cppyy_scope_t)s_scope_id] = info;
        } // -- class payload

        //====================================================================

        { // class cppyy_test_data --
        s_handles["cppyy_test_data"] = (cppyy_scope_t)++s_scope_id;

        std::vector<Cppyy_PseudoMethodInfo> methods;

        // cppyy_test_data()
        std::vector<std::string> argtypes;
        methods.push_back(Cppyy_PseudoMethodInfo("cppyy_test_data", argtypes, "constructor", kConstructor));
        s_methods["cppyy_test_data::cppyy_test_data"] = s_method_id++;

        methods.push_back(Cppyy_PseudoMethodInfo("destroy_arrays", argtypes, "void"));
        s_methods["cppyy_test_data::destroy_arrays"] = s_method_id++;

        std::vector<Cppyy_PseudoDatambrInfo> data;
        PUBLIC_CPPYY_DATA2(bool,    bool);
        PUBLIC_CPPYY_DATA (char,    char);
        PUBLIC_CPPYY_DATA (uchar,   unsigned char);
        PUBLIC_CPPYY_DATA3(short,   short,              h);
        PUBLIC_CPPYY_DATA3(ushort,  unsigned short,     H);
        PUBLIC_CPPYY_DATA3(int,     int,                i);
        PUBLIC_CPPYY_DATA3(uint,    unsigned int,       I);
        PUBLIC_CPPYY_DATA3(long,    long,               l);
        PUBLIC_CPPYY_DATA3(ulong,   unsigned long,      L);
        PUBLIC_CPPYY_DATA (llong,   long long);
        PUBLIC_CPPYY_DATA (ullong,  unsigned long long);
        PUBLIC_CPPYY_DATA3(float,   float,              f);
        PUBLIC_CPPYY_DATA3(double,  double,             d);
        PUBLIC_CPPYY_DATA (enum,    cppyy_test_data::what);
        PUBLIC_CPPYY_DATA (voidp,   void*);

        PUBLIC_CPPYY_STATIC_DATA(char,    char);
        PUBLIC_CPPYY_STATIC_DATA(uchar,   unsigned char);
        PUBLIC_CPPYY_STATIC_DATA(short,   short);
        PUBLIC_CPPYY_STATIC_DATA(ushort,  unsigned short);
        PUBLIC_CPPYY_STATIC_DATA(int,     int);
        PUBLIC_CPPYY_STATIC_DATA(uint,    unsigned int);
        PUBLIC_CPPYY_STATIC_DATA(long,    long);
        PUBLIC_CPPYY_STATIC_DATA(ulong,   unsigned long);
        PUBLIC_CPPYY_STATIC_DATA(llong,   long long);
        PUBLIC_CPPYY_STATIC_DATA(ullong,  unsigned long long);
        PUBLIC_CPPYY_STATIC_DATA(float,   float);
        PUBLIC_CPPYY_STATIC_DATA(double,  double);
        PUBLIC_CPPYY_STATIC_DATA(enum,    cppyy_test_data::what);
        PUBLIC_CPPYY_STATIC_DATA(voidp,   void*);

        Cppyy_PseudoClassInfo info(methods, s_method_id - methods.size(), data);
        s_scopes[(cppyy_scope_t)s_scope_id] = info;
        } // -- class cppyy_test_data

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
    long idx = (long)method;
    if (idx == s_methods["static_example01::staticSetPayload_payload*_double"]) {
        assert(!self && nargs == 2);
        dummy::example01::staticSetPayload((dummy::payload*)(*(long*)&((CPPYY_G__value*)args)[0]),
           ((CPPYY_G__value*)args)[1].obj.d);
    } else if (idx == s_methods["static_example01::setCount_int"]) {
        assert(!self && nargs == 1);
        dummy::example01::setCount(((CPPYY_G__value*)args)[0].obj.in);
    } else if (idx == s_methods["example01::setPayload_payload*"]) {
        assert(self && nargs == 1);
        ((dummy::example01*)self)->setPayload((dummy::payload*)(*(long*)&((CPPYY_G__value*)args)[0]));
    } else if (idx == s_methods["cppyy_test_data::destroy_arrays"]) {
        assert(self && nargs == 0);
        ((dummy::cppyy_test_data*)self)->destroy_arrays();
    } else if (idx == s_methods["cppyy_test_data::set_bool"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_bool((bool)((CPPYY_G__value*)args)[0].obj.i);
    } else if (idx == s_methods["cppyy_test_data::set_char"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_char(((CPPYY_G__value*)args)[0].obj.ch);
    } else if (idx == s_methods["cppyy_test_data::set_uchar"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_uchar(((CPPYY_G__value*)args)[0].obj.uch);
    } else if (idx == s_methods["cppyy_test_data::set_short"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_short(((CPPYY_G__value*)args)[0].obj.sh);
    } else if (idx == s_methods["cppyy_test_data::set_short_c"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_short_c(*(short*)&((CPPYY_G__value*)args)[0]);
    } else if (idx == s_methods["cppyy_test_data::set_ushort"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_ushort(((CPPYY_G__value*)args)[0].obj.ush);
    } else if (idx == s_methods["cppyy_test_data::set_ushort_c"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_ushort_c(*(unsigned short*)&((CPPYY_G__value*)args)[0]);
    } else if (idx == s_methods["cppyy_test_data::set_int"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_int(((CPPYY_G__value*)args)[0].obj.in);
    } else if (idx == s_methods["cppyy_test_data::set_int_c"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_int_c(*(int*)&((CPPYY_G__value*)args)[0]);
    } else if (idx == s_methods["cppyy_test_data::set_uint"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_uint(((CPPYY_G__value*)args)[0].obj.uin);
    } else if (idx == s_methods["cppyy_test_data::set_uint_c"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_uint_c(*(unsigned int*)&((CPPYY_G__value*)args)[0]);
    } else if (idx == s_methods["cppyy_test_data::set_long"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_long(((CPPYY_G__value*)args)[0].obj.i);
    } else if (idx == s_methods["cppyy_test_data::set_long_c"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_long_c(*(long*)&((CPPYY_G__value*)args)[0]);
    } else if (idx == s_methods["cppyy_test_data::set_ulong"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_ulong(((CPPYY_G__value*)args)[0].obj.ulo);
    } else if (idx == s_methods["cppyy_test_data::set_ulong_c"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_ulong_c(*(unsigned long*)&((CPPYY_G__value*)args)[0]);
    } else if (idx == s_methods["cppyy_test_data::set_llong"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_llong(((CPPYY_G__value*)args)[0].obj.ll);
    } else if (idx == s_methods["cppyy_test_data::set_llong_c"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_llong_c(*(long long*)&((CPPYY_G__value*)args)[0]);
    } else if (idx == s_methods["cppyy_test_data::set_ullong"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_ullong(((CPPYY_G__value*)args)[0].obj.ull);
    } else if (idx == s_methods["cppyy_test_data::set_ullong_c"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_ullong_c(*(unsigned long*)&((CPPYY_G__value*)args)[0]);
    } else if (idx == s_methods["cppyy_test_data::set_float"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_float(((CPPYY_G__value*)args)[0].obj.fl);
    } else if (idx == s_methods["cppyy_test_data::set_float_c"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_float_c(*(float*)&((CPPYY_G__value*)args)[0]);
    } else if (idx == s_methods["cppyy_test_data::set_double"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_double(((CPPYY_G__value*)args)[0].obj.d);
    } else if (idx == s_methods["cppyy_test_data::set_double_c"]) {
        assert(self && nargs == 1);
        ((dummy::cppyy_test_data*)self)->set_double_c(*(double*)&((CPPYY_G__value*)args)[0]);
    } else {
        assert(!"method unknown in cppyy_call_v");
    }
}

unsigned char cppyy_call_b(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    unsigned char result = 0;
    const long idx = (long)method;
    if (idx == s_methods["cppyy_test_data::get_bool"]) {
        assert(self && nargs == 0);
        result = (unsigned char)((dummy::cppyy_test_data*)self)->get_bool();
    } else {
        assert(!"method unknown in cppyy_call_b");
    }
    return result;
}

char cppyy_call_c(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    char result = 0;
    const long idx = (long)method;
    if (idx == s_methods["cppyy_test_data::get_char"]) {
        assert(self && nargs == 0);
        result = ((dummy::cppyy_test_data*)self)->get_char();
    } else if (idx == s_methods["cppyy_test_data::get_uchar"]) {
        assert(self && nargs == 0);
        result = (char)((dummy::cppyy_test_data*)self)->get_uchar();
    } else {
        assert(!"method unknown in cppyy_call_c");
    } 
    return result;
}

short cppyy_call_h(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    short result = 0;
    const long idx = (long)method; 
    if (idx == s_methods["cppyy_test_data::get_short"]) {
        assert(self && nargs == 0);
        result = ((dummy::cppyy_test_data*)self)->get_short();
    } else if (idx == s_methods["cppyy_test_data::get_ushort"]) {
        assert(self && nargs == 0);
        result = (short)((dummy::cppyy_test_data*)self)->get_ushort();
    } else {
        assert(!"method unknown in cppyy_call_h");
    }   
    return result;
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
    } else if (idx == s_methods["cppyy_test_data::get_int"]) {
        assert(self && nargs == 0);
        result = ((dummy::cppyy_test_data*)self)->get_int();
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
    } else if (idx == s_methods["cppyy_test_data::get_uint"]) {
        assert(self && nargs == 0);
        result = (long)((dummy::cppyy_test_data*)self)->get_uint();
    } else if (idx == s_methods["cppyy_test_data::get_long"]) {
        assert(self && nargs == 0);
        result = ((dummy::cppyy_test_data*)self)->get_long();
    } else if (idx == s_methods["cppyy_test_data::get_ulong"]) {
        assert(self && nargs == 0);
        result = (long)((dummy::cppyy_test_data*)self)->get_ulong();
    } else if (idx == s_methods["cppyy_test_data::get_bool_array"]) {
        assert(self && nargs == 0);
        result = (long)((dummy::cppyy_test_data*)self)->get_bool_array();
    } else if (idx == s_methods["cppyy_test_data::get_bool_array2"]) {
        assert(self && nargs == 0);
        result = (long)((dummy::cppyy_test_data*)self)->get_bool_array2();
    } else if (idx == s_methods["cppyy_test_data::get_short_array"]) {
        assert(self && nargs == 0);
        result = (long)((dummy::cppyy_test_data*)self)->get_short_array();
    } else if (idx == s_methods["cppyy_test_data::get_short_array2"]) {
        assert(self && nargs == 0);
        result = (long)((dummy::cppyy_test_data*)self)->get_short_array2();
    } else if (idx == s_methods["cppyy_test_data::get_ushort_array"]) {
        assert(self && nargs == 0);
        result = (long)((dummy::cppyy_test_data*)self)->get_ushort_array();
    } else if (idx == s_methods["cppyy_test_data::get_ushort_array2"]) {
        assert(self && nargs == 0);
        result = (long)((dummy::cppyy_test_data*)self)->get_ushort_array2();
    } else if (idx == s_methods["cppyy_test_data::get_int_array"]) {
        assert(self && nargs == 0);
        result = (long)((dummy::cppyy_test_data*)self)->get_int_array();
    } else if (idx == s_methods["cppyy_test_data::get_int_array2"]) {
        assert(self && nargs == 0);
        result = (long)((dummy::cppyy_test_data*)self)->get_int_array2();
    } else if (idx == s_methods["cppyy_test_data::get_uint_array"]) {
        assert(self && nargs == 0);
        result = (long)((dummy::cppyy_test_data*)self)->get_uint_array();
    } else if (idx == s_methods["cppyy_test_data::get_uint_array2"]) {
        assert(self && nargs == 0);
        result = (long)((dummy::cppyy_test_data*)self)->get_uint_array2();
    } else if (idx == s_methods["cppyy_test_data::get_long_array"]) {
        assert(self && nargs == 0);
        result = (long)((dummy::cppyy_test_data*)self)->get_long_array();
    } else if (idx == s_methods["cppyy_test_data::get_long_array2"]) {
        assert(self && nargs == 0);
        result = (long)((dummy::cppyy_test_data*)self)->get_long_array2();
    } else if (idx == s_methods["cppyy_test_data::get_ulong_array"]) {
        assert(self && nargs == 0);
        result = (long)((dummy::cppyy_test_data*)self)->get_ulong_array();
    } else if (idx == s_methods["cppyy_test_data::get_ulong_array2"]) {
        assert(self && nargs == 0);
        result = (long)((dummy::cppyy_test_data*)self)->get_ulong_array2();
    } else if (idx == s_methods["cppyy_test_data::pass_array_short"]) {
        assert(self && nargs == 1);
        result = (long)((dummy::cppyy_test_data*)self)->pass_array(
           (*(short**)&((CPPYY_G__value*)args)[0]));
    } else if (idx == s_methods["cppyy_test_data::pass_void_array_h"]) {
        assert(self && nargs == 1);
        result = (long)((dummy::cppyy_test_data*)self)->pass_void_array_h(
           (*(short**)&((CPPYY_G__value*)args)[0]));
    } else if (idx == s_methods["cppyy_test_data::pass_array_ushort"]) {
        assert(self && nargs == 1);
        result = (long)((dummy::cppyy_test_data*)self)->pass_array(
           (*(unsigned short**)&((CPPYY_G__value*)args)[0]));
    } else if (idx == s_methods["cppyy_test_data::pass_void_array_H"]) {
        assert(self && nargs == 1);
        result = (long)((dummy::cppyy_test_data*)self)->pass_void_array_H(
           (*(unsigned short**)&((CPPYY_G__value*)args)[0]));
    } else if (idx == s_methods["cppyy_test_data::pass_array_int"]) {
        assert(self && nargs == 1);
        result = (long)((dummy::cppyy_test_data*)self)->pass_array(
           (*(int**)&((CPPYY_G__value*)args)[0]));
    } else if (idx == s_methods["cppyy_test_data::pass_void_array_i"]) {
        assert(self && nargs == 1);
        result = (long)((dummy::cppyy_test_data*)self)->pass_void_array_i(
           (*(int**)&((CPPYY_G__value*)args)[0]));
    } else if (idx == s_methods["cppyy_test_data::pass_array_uint"]) {
        assert(self && nargs == 1);
        result = (long)((dummy::cppyy_test_data*)self)->pass_array(
           (*(unsigned int**)&((CPPYY_G__value*)args)[0]));
    } else if (idx == s_methods["cppyy_test_data::pass_void_array_I"]) {
        assert(self && nargs == 1);
        result = (long)((dummy::cppyy_test_data*)self)->pass_void_array_I(
           (*(unsigned int**)&((CPPYY_G__value*)args)[0]));
    } else if (idx == s_methods["cppyy_test_data::pass_array_long"]) {
        assert(self && nargs == 1);
        result = (long)((dummy::cppyy_test_data*)self)->pass_array(
           (*(long**)&((CPPYY_G__value*)args)[0]));
    } else if (idx == s_methods["cppyy_test_data::pass_void_array_l"]) {
        assert(self && nargs == 1);
        result = (long)((dummy::cppyy_test_data*)self)->pass_void_array_l(
           (*(long**)&((CPPYY_G__value*)args)[0]));
    } else if (idx == s_methods["cppyy_test_data::pass_array_ulong"]) {
        assert(self && nargs == 1);
        result = (long)((dummy::cppyy_test_data*)self)->pass_array(
           (*(unsigned long**)&((CPPYY_G__value*)args)[0]));
    } else if (idx == s_methods["cppyy_test_data::pass_void_array_L"]) {
        assert(self && nargs == 1);
        result = (long)((dummy::cppyy_test_data*)self)->pass_void_array_L(
           (*(unsigned long**)&((CPPYY_G__value*)args)[0]));
    } else if (idx == s_methods["cppyy_test_data::pass_array_float"]) {
        assert(self && nargs == 1);
        result = (long)((dummy::cppyy_test_data*)self)->pass_array(
           (*(float**)&((CPPYY_G__value*)args)[0]));
    } else if (idx == s_methods["cppyy_test_data::pass_void_array_f"]) {
        assert(self && nargs == 1);
        result = (long)((dummy::cppyy_test_data*)self)->pass_void_array_f(
           (*(float**)&((CPPYY_G__value*)args)[0]));
    } else if (idx == s_methods["cppyy_test_data::pass_array_double"]) {
        assert(self && nargs == 1);
        result = (long)((dummy::cppyy_test_data*)self)->pass_array(
           (*(double**)&((CPPYY_G__value*)args)[0]));
    } else if (idx == s_methods["cppyy_test_data::pass_void_array_d"]) {
        assert(self && nargs == 1);
        result = (long)((dummy::cppyy_test_data*)self)->pass_void_array_d(
           (*(double**)&((CPPYY_G__value*)args)[0]));
    } else {
        assert(!"method unknown in cppyy_call_l");
    }
    return result;
}

long long cppyy_call_ll(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    long long result = 0;
    const long idx = (long)method;
    if (idx == s_methods["cppyy_test_data::get_llong"]) {
        assert(self && nargs == 0);
        result = ((dummy::cppyy_test_data*)self)->get_llong();
    } else if (idx == s_methods["cppyy_test_data::get_ullong"]) {
        assert(self && nargs == 0);
        result = (long long)((dummy::cppyy_test_data*)self)->get_ullong();
    } else {
        assert(!"method unknown in cppyy_call_ll");
    }
    return result;
}   

float cppyy_call_f(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    float result = 0;
    const long idx = (long)method;
    if (idx == s_methods["cppyy_test_data::get_float"]) {
        assert(self && nargs == 0);
        result = ((dummy::cppyy_test_data*)self)->get_float();
    } else {
        assert(!"method unknown in cppyy_call_f");
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
    } else if (idx == s_methods["cppyy_test_data::get_double"]) {
        assert(self && nargs == 0);
        result = ((dummy::cppyy_test_data*)self)->get_double();
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
        assert(nargs == 0 || nargs == 1);
        if (nargs == 0) result = new dummy::payload;
        else if (nargs == 1) result = new dummy::payload(((CPPYY_G__value*)args)[0].obj.d);
    } else if (idx == s_methods["cppyy_test_data::cppyy_test_data"]) {
        assert(nargs == 0);
        result = new dummy::cppyy_test_data;
    } else {
        assert(!"method unknown in cppyy_constructor");
    }       
    return (cppyy_object_t)result;
}

cppyy_methptrgetter_t cppyy_get_methptr_getter(cppyy_type_t /* handle */, cppyy_index_t /* method_index */) {
    return (cppyy_methptrgetter_t)0;
}


/* handling of function argument buffer ----------------------------------- */
void* cppyy_allocate_function_args(int nargs) {
    CPPYY_G__value* args = (CPPYY_G__value*)malloc(nargs*sizeof(CPPYY_G__value));
    for (int i = 0; i < nargs; ++i)
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
int cppyy_num_datamembers(cppyy_scope_t handle) {
    return s_scopes[handle].m_datambrs.size();
}

char* cppyy_datamember_name(cppyy_scope_t handle, int idatambr) {
    return cppstring_to_cstring(s_scopes[handle].m_datambrs[idatambr].m_name);
}

char* cppyy_datamember_type(cppyy_scope_t handle, int idatambr) {
    return cppstring_to_cstring(s_scopes[handle].m_datambrs[idatambr].m_type);
}

ptrdiff_t cppyy_datamember_offset(cppyy_scope_t handle, int idatambr) {
    return s_scopes[handle].m_datambrs[idatambr].m_offset;
}


/* data member properties ------------------------------------------------  */
int cppyy_is_publicdata(cppyy_scope_t handle, int idatambr) {
    return 1;
}

int cppyy_is_staticdata(cppyy_scope_t handle, int idatambr) {
    return s_scopes[handle].m_datambrs[idatambr].m_isstatic;
}


/* misc helpers ----------------------------------------------------------- */
#if defined(_MSC_VER)
long long cppyy_strtoll(const char* str) {
    return _strtoi64(str, NULL, 0);
}

extern "C" {
unsigned long long cppyy_strtoull(const char* str) {
    return _strtoui64(str, NULL, 0);
}
}
#else
long long cppyy_strtoll(const char* str) {
    return strtoll(str, NULL, 0);
}

extern "C" {
unsigned long long cppyy_strtoull(const char* str) {
    return strtoull(str, NULL, 0);
}
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
