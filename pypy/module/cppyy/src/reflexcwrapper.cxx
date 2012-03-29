#include "cppyy.h"
#include "reflexcwrapper.h"

#include "Reflex/Kernel.h"
#include "Reflex/Type.h"
#include "Reflex/Base.h"
#include "Reflex/Member.h"
#include "Reflex/Object.h"
#include "Reflex/Builder/TypeBuilder.h"
#include "Reflex/PropertyList.h"
#include "Reflex/TypeTemplate.h"

#include <string>
#include <sstream>
#include <utility>
#include <vector>

#include <assert.h>
#include <stdlib.h>


/* local helpers ---------------------------------------------------------- */
static inline char* cppstring_to_cstring(const std::string& name) {
    char* name_char = (char*)malloc(name.size() + 1);
    strcpy(name_char, name.c_str());
    return name_char;
}

static inline Reflex::Scope scope_from_handle(cppyy_type_t handle) {
    return Reflex::Scope((Reflex::ScopeName*)handle);
}

static inline Reflex::Type type_from_handle(cppyy_type_t handle) {
    return Reflex::Scope((Reflex::ScopeName*)handle);
}

static inline std::vector<void*> build_args(int nargs, void* args) {
    std::vector<void*> arguments;
    arguments.reserve(nargs);
    for (int i = 0; i < nargs; ++i) {
	char tc = ((CPPYY_G__value*)args)[i].type;
        if (tc != 'a' && tc != 'o')
            arguments.push_back(&((CPPYY_G__value*)args)[i]);
        else
            arguments.push_back((void*)(*(long*)&((CPPYY_G__value*)args)[i]));
    }
    return arguments;
}


/* name to opaque C++ scope representation -------------------------------- */
char* cppyy_resolve_name(const char* cppitem_name) {
    Reflex::Scope s = Reflex::Scope::ByName(cppitem_name);
    if (s.IsEnum())
        return cppstring_to_cstring("unsigned int");
    const std::string& name = s.Name(Reflex::SCOPED|Reflex::QUALIFIED|Reflex::FINAL);
    if (name.empty())
        return cppstring_to_cstring(cppitem_name);
    return cppstring_to_cstring(name);
}

cppyy_scope_t cppyy_get_scope(const char* scope_name) {
    Reflex::Scope s = Reflex::Scope::ByName(scope_name);
    if (s.IsEnum())     // pretend to be builtin by returning 0
        return (cppyy_type_t)0;
    return (cppyy_type_t)s.Id();
}

cppyy_type_t cppyy_get_template(const char* template_name) {
   Reflex::TypeTemplate tt = Reflex::TypeTemplate::ByName(template_name);
   return (cppyy_type_t)tt.Id();
}

cppyy_type_t cppyy_get_object_type(cppyy_type_t klass, cppyy_object_t obj) {
    Reflex::Type t = type_from_handle(klass);
    Reflex::Type tActual = t.DynamicType(Reflex::Object(t, (void*)obj));
    if (tActual && tActual != t) {
        // TODO: lookup through name should not be needed (but tActual.Id()
        // does not return a singular Id for the system :( )
        return (cppyy_type_t)cppyy_get_scope(tActual.Name().c_str());
    }
    return klass;
}


/* memory management ------------------------------------------------------ */
cppyy_object_t cppyy_allocate(cppyy_type_t handle) {
    Reflex::Type t = type_from_handle(handle);
    return (cppyy_object_t)t.Allocate();
}

void cppyy_deallocate(cppyy_type_t handle, cppyy_object_t instance) {
    Reflex::Type t = type_from_handle(handle);
    t.Deallocate((void*)instance);
}

void cppyy_destruct(cppyy_type_t handle, cppyy_object_t self) {
    Reflex::Type t = type_from_handle(handle);
    t.Destruct((void*)self, true);
}


/* method/function dispatching -------------------------------------------- */
void cppyy_call_v(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    std::vector<void*> arguments = build_args(nargs, args);
    Reflex::StubFunction stub = (Reflex::StubFunction)method;
    stub(NULL /* return address */, (void*)self, arguments, NULL /* stub context */);
}

template<typename T>
static inline T cppyy_call_T(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    T result;
    std::vector<void*> arguments = build_args(nargs, args);
    Reflex::StubFunction stub = (Reflex::StubFunction)method;
    stub(&result, (void*)self, arguments, NULL /* stub context */);
    return result;
}

int cppyy_call_b(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    return (int)cppyy_call_T<bool>(method, self, nargs, args);
}

char cppyy_call_c(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    return cppyy_call_T<char>(method, self, nargs, args);
}

short cppyy_call_h(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    return cppyy_call_T<short>(method, self, nargs, args);
}

int cppyy_call_i(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    return cppyy_call_T<int>(method, self, nargs, args);
}

long cppyy_call_l(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    return cppyy_call_T<long>(method, self, nargs, args);
}

double cppyy_call_f(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    return cppyy_call_T<float>(method, self, nargs, args);
}

double cppyy_call_d(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    return cppyy_call_T<double>(method, self, nargs, args);
}   

void* cppyy_call_r(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    return (void*)cppyy_call_T<long>(method, self, nargs, args);
}

char* cppyy_call_s(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    std::string result("");
    std::vector<void*> arguments = build_args(nargs, args);
    Reflex::StubFunction stub = (Reflex::StubFunction)method;
    stub(&result, (void*)self, arguments, NULL /* stub context */);
    return cppstring_to_cstring(result);
}

void cppyy_constructor(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    cppyy_call_v(method, self, nargs, args);
}

cppyy_object_t cppyy_call_o(cppyy_method_t method, cppyy_object_t self, int nargs, void* args,
                  cppyy_type_t result_type) {
    void* result = (void*)cppyy_allocate(result_type);
    std::vector<void*> arguments = build_args(nargs, args);
    Reflex::StubFunction stub = (Reflex::StubFunction)method;
    stub(result, (void*)self, arguments, NULL /* stub context */);
    return (cppyy_object_t)result;
}

static cppyy_methptrgetter_t get_methptr_getter(Reflex::Member m) {
    Reflex::PropertyList plist = m.Properties();
    if (plist.HasProperty("MethPtrGetter")) {
        Reflex::Any& value = plist.PropertyValue("MethPtrGetter");
        return (cppyy_methptrgetter_t)Reflex::any_cast<void*>(value);
    }
    return 0;
}

cppyy_methptrgetter_t cppyy_get_methptr_getter(cppyy_type_t handle, int method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    return get_methptr_getter(m);
}


/* handling of function argument buffer ----------------------------------- */
void* cppyy_allocate_function_args(size_t nargs) {
    CPPYY_G__value* args = (CPPYY_G__value*)malloc(nargs*sizeof(CPPYY_G__value));
    for (size_t i = 0; i < nargs; ++i)
        args[i].type = 'l';
    return (void*)args;
}

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
int cppyy_is_namespace(cppyy_scope_t handle) {
    Reflex::Scope s = scope_from_handle(handle);
    return s.IsNamespace();
}

int cppyy_is_enum(const char* type_name) {
    Reflex::Type t = Reflex::Type::ByName(type_name);
    return t.IsEnum();
}


/* class reflection information ------------------------------------------- */
char* cppyy_final_name(cppyy_type_t handle) {
    Reflex::Scope s = scope_from_handle(handle);
    if (s.IsEnum())
        return cppstring_to_cstring("unsigned int");
    std::string name = s.Name(Reflex::FINAL);
    return cppstring_to_cstring(name);
}

char* cppyy_scoped_final_name(cppyy_type_t handle) {
    Reflex::Scope s = scope_from_handle(handle);
    if (s.IsEnum())
        return cppstring_to_cstring("unsigned int");
    std::string name = s.Name(Reflex::SCOPED | Reflex::FINAL);
    return cppstring_to_cstring(name);
}   

static int cppyy_has_complex_hierarchy(const Reflex::Type& t) {
    int is_complex = 1;
    
    size_t nbases = t.BaseSize();
    if (1 < nbases)
        is_complex = 1;
    else if (nbases == 0)
        is_complex = 0;
    else {         // one base class only
        Reflex::Base b = t.BaseAt(0);
        if (b.IsVirtual())
            is_complex = 1;       // TODO: verify; can be complex, need not be.
        else
            is_complex = cppyy_has_complex_hierarchy(t.BaseAt(0).ToType());
    }

    return is_complex;
}   

int cppyy_has_complex_hierarchy(cppyy_type_t handle) {
    Reflex::Type t = type_from_handle(handle);
    return cppyy_has_complex_hierarchy(t);
}

int cppyy_num_bases(cppyy_type_t handle) {
    Reflex::Type t = type_from_handle(handle);
    return t.BaseSize();
}

char* cppyy_base_name(cppyy_type_t handle, int base_index) {
    Reflex::Type t = type_from_handle(handle);
    Reflex::Base b = t.BaseAt(base_index);
    std::string name = b.Name(Reflex::FINAL|Reflex::SCOPED);
    return cppstring_to_cstring(name);
}

int cppyy_is_subtype(cppyy_type_t derived_handle, cppyy_type_t base_handle) {
    Reflex::Type derived_type = type_from_handle(derived_handle);
    Reflex::Type base_type = type_from_handle(base_handle);
    return (int)derived_type.HasBase(base_type);
}

size_t cppyy_base_offset(cppyy_type_t derived_handle, cppyy_type_t base_handle, cppyy_object_t address) {
    Reflex::Type derived_type = type_from_handle(derived_handle);
    Reflex::Type base_type = type_from_handle(base_handle);

    // when dealing with virtual inheritance the only (reasonably) well-defined info is
    // in a Reflex internal base table, that contains all offsets within the hierarchy
    Reflex::Member getbases = derived_type.FunctionMemberByName(
           "__getBasesTable", Reflex::Type(), 0, Reflex::INHERITEDMEMBERS_NO, Reflex::DELAYEDLOAD_OFF);
    if (getbases) {
        typedef std::vector<std::pair<Reflex::Base, int> > Bases_t;
        Bases_t* bases;
        Reflex::Object bases_holder(Reflex::Type::ByTypeInfo(typeid(Bases_t)), &bases);
        getbases.Invoke(&bases_holder);

        for (Bases_t::iterator ibase = bases->begin(); ibase != bases->end(); ++ibase) {
            if (ibase->first.ToType() == base_type)
                return (size_t)ibase->first.Offset((void*)address);
        }

        // contrary to typical invoke()s, the result of the internal getbases function
        // is a pointer to a function static, so no delete
    }

    return 0;
}


/* method/function reflection information --------------------------------- */
int cppyy_num_methods(cppyy_scope_t handle) {
    Reflex::Scope s = scope_from_handle(handle);
    return s.FunctionMemberSize();
}

char* cppyy_method_name(cppyy_scope_t handle, int method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    std::string name;
    if (m.IsConstructor())
        name = s.Name(Reflex::FINAL);   // to get proper name for templates
    else
        name = m.Name();
    return cppstring_to_cstring(name);
}

char* cppyy_method_result_type(cppyy_scope_t handle, int method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    Reflex::Type rt = m.TypeOf().ReturnType();
    std::string name = rt.Name(Reflex::FINAL|Reflex::SCOPED|Reflex::QUALIFIED);
    return cppstring_to_cstring(name);
}

int cppyy_method_num_args(cppyy_scope_t handle, int method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    return m.FunctionParameterSize();
}

int cppyy_method_req_args(cppyy_scope_t handle, int method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    return m.FunctionParameterSize(true);
}

char* cppyy_method_arg_type(cppyy_scope_t handle, int method_index, int arg_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    Reflex::Type at = m.TypeOf().FunctionParameterAt(arg_index);
    std::string name = at.Name(Reflex::FINAL|Reflex::SCOPED|Reflex::QUALIFIED);
    return cppstring_to_cstring(name);
}

char* cppyy_method_arg_default(cppyy_scope_t handle, int method_index, int arg_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    std::string dflt = m.FunctionParameterDefaultAt(arg_index);
    return cppstring_to_cstring(dflt);
}

char* cppyy_method_signature(cppyy_scope_t handle, int method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    Reflex::Type mt = m.TypeOf();
    std::ostringstream sig;
    sig << s.Name(Reflex::SCOPED) << "::" << m.Name() << "(";
    int nArgs = m.FunctionParameterSize();
    for (int iarg = 0; iarg < nArgs; ++iarg) {
        sig << mt.FunctionParameterAt(iarg).Name(Reflex::SCOPED|Reflex::QUALIFIED);
        if (iarg != nArgs-1)
            sig << ", ";
    }
    sig << ")" << std::ends;
    return cppstring_to_cstring(sig.str());
}

cppyy_method_t cppyy_get_method(cppyy_scope_t handle, int method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    assert(m.IsFunctionMember());
    return (cppyy_method_t)m.Stubfunction();
}


/* method properties -----------------------------------------------------  */
int cppyy_is_constructor(cppyy_type_t handle, int method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    return m.IsConstructor();
}

int cppyy_is_staticmethod(cppyy_type_t handle, int method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    return m.IsStatic();
}


/* data member reflection information ------------------------------------- */
int cppyy_num_data_members(cppyy_scope_t handle) {
    Reflex::Scope s = scope_from_handle(handle);
    // fix enum representation by adding them to the containing scope as per C++
    // TODO: this (relatively harmlessly) dupes data members when updating in the
    //       case s is a namespace
    for (int isub = 0; isub < (int)s.ScopeSize(); ++isub) {
        Reflex::Scope sub = s.SubScopeAt(isub);
        if (sub.IsEnum()) {
            for (int idata = 0;  idata < (int)sub.DataMemberSize(); ++idata) {
                Reflex::Member m = sub.DataMemberAt(idata);
                s.AddDataMember(m.Name().c_str(), sub, 0,
                                Reflex::PUBLIC|Reflex::STATIC|Reflex::ARTIFICIAL,
                                (char*)m.Offset());
            }
        }
    }
    return s.DataMemberSize();
}

char* cppyy_data_member_name(cppyy_scope_t handle, int data_member_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.DataMemberAt(data_member_index);
    std::string name = m.Name();
    return cppstring_to_cstring(name);
}

char* cppyy_data_member_type(cppyy_scope_t handle, int data_member_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.DataMemberAt(data_member_index);
    std::string name = m.TypeOf().Name(Reflex::FINAL|Reflex::SCOPED|Reflex::QUALIFIED);
    return cppstring_to_cstring(name);
}

size_t cppyy_data_member_offset(cppyy_scope_t handle, int data_member_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.DataMemberAt(data_member_index);
    if (m.IsArtificial() && m.TypeOf().IsEnum())
        return (size_t)&m.InterpreterOffset();
    return m.Offset();
}


/* data member properties ------------------------------------------------  */
int cppyy_is_publicdata(cppyy_scope_t handle, int data_member_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.DataMemberAt(data_member_index);
    return m.IsPublic();
}

int cppyy_is_staticdata(cppyy_scope_t handle, int data_member_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.DataMemberAt(data_member_index);
    return m.IsStatic();
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
    return (cppyy_object_t)new std::string(str);
}

cppyy_object_t cppyy_stdstring2stdstring(cppyy_object_t ptr) {
    return (cppyy_object_t)new std::string(*(std::string*)ptr);
}

void cppyy_free_stdstring(cppyy_object_t ptr) {
    delete (std::string*)ptr;
}
