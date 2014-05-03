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

#define private public
#include "Reflex/PluginService.h"
#undef private

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
int cppyy_num_scopes(cppyy_scope_t handle) {
    Reflex::Scope s = scope_from_handle(handle);
    return s.SubScopeSize();
}

char* cppyy_scope_name(cppyy_scope_t handle, int iscope) {
    Reflex::Scope s = scope_from_handle(handle);
    std::string name = s.SubScopeAt(iscope).Name(Reflex::F);
    return cppstring_to_cstring(name);
}

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
    if (!s) Reflex::PluginService::Instance().LoadFactoryLib(scope_name);
    s = Reflex::Scope::ByName(scope_name);
    if (s.IsEnum())     // pretend to be builtin by returning 0
        return (cppyy_type_t)0;
    return (cppyy_type_t)s.Id();
}

cppyy_type_t cppyy_get_template(const char* template_name) {
   Reflex::TypeTemplate tt = Reflex::TypeTemplate::ByName(template_name);
   return (cppyy_type_t)tt.Id();
}

cppyy_type_t cppyy_actual_class(cppyy_type_t klass, cppyy_object_t obj) {
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

unsigned char cppyy_call_b(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    return (unsigned char)cppyy_call_T<bool>(method, self, nargs, args);
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

long long cppyy_call_ll(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    return cppyy_call_T<long long>(method, self, nargs, args);
}

float cppyy_call_f(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    return cppyy_call_T<float>(method, self, nargs, args);
}

double cppyy_call_d(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    return cppyy_call_T<double>(method, self, nargs, args);
}

void* cppyy_call_r(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    return (void*)cppyy_call_T<long>(method, self, nargs, args);
}

char* cppyy_call_s(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    std::string* cppresult = (std::string*)malloc(sizeof(std::string));
    std::vector<void*> arguments = build_args(nargs, args);
    Reflex::StubFunction stub = (Reflex::StubFunction)method;
    stub(cppresult, (void*)self, arguments, NULL /* stub context */);
    char* cstr = cppstring_to_cstring(*cppresult);
    cppresult->std::string::~string();
    free((void*)cppresult);        // the stub will have performed a placement-new
    return cstr;
}

cppyy_object_t cppyy_constructor(cppyy_method_t method, cppyy_type_t handle, int nargs, void* args) {
    cppyy_object_t self = cppyy_allocate(handle);
    cppyy_call_v(method, self, nargs, args);
    return self;
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

cppyy_methptrgetter_t cppyy_get_methptr_getter(cppyy_type_t handle, cppyy_index_t method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    return get_methptr_getter(m);
}


/* handling of function argument buffer ----------------------------------- */
void* cppyy_allocate_function_args(int nargs) {
    CPPYY_G__value* args = (CPPYY_G__value*)malloc(nargs*sizeof(CPPYY_G__value));
    for (int i = 0; i < nargs; ++i)
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
    std::string name = t.Name(Reflex::FINAL|Reflex::SCOPED);
    if (5 < name.size() && name.substr(0, 5) == "std::") {
        // special case: STL base classes are usually unnecessary,
        // so either build all (i.e. if available) or none
        for (int i=0; i < (int)t.BaseSize(); ++i)
            if (!t.BaseAt(i)) return 0;
    }
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

ptrdiff_t cppyy_base_offset(cppyy_type_t derived_handle, cppyy_type_t base_handle,
                       cppyy_object_t address, int direction) {
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

        // if direction is down-cast, perform the cast in C++ first in order to ensure
        // we have a derived object for accessing internal offset pointers
        if (direction < 0) {
           Reflex::Object o(base_type, (void*)address);
           address = (cppyy_object_t)o.CastObject(derived_type).Address();
        }

        for (Bases_t::iterator ibase = bases->begin(); ibase != bases->end(); ++ibase) {
            if (ibase->first.ToType() == base_type) {
                long offset = (long)ibase->first.Offset((void*)address);
                if (direction < 0)
                    return (ptrdiff_t) -offset;  // note negative; rolls over
                return (ptrdiff_t)offset;
            }
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

cppyy_index_t cppyy_method_index_at(cppyy_scope_t scope, int imeth) {
    return (cppyy_index_t)imeth;
}

cppyy_index_t* cppyy_method_indices_from_name(cppyy_scope_t handle, const char* name) {
    std::vector<cppyy_index_t> result;
    Reflex::Scope s = scope_from_handle(handle);
    // the following appears dumb, but the internal storage for Reflex is an
    // unsorted std::vector anyway, so there's no gain to be had in using the
    // Scope::FunctionMemberByName() function
    int num_meth = s.FunctionMemberSize();
    for (int imeth = 0; imeth < num_meth; ++imeth) {
        Reflex::Member m = s.FunctionMemberAt(imeth);
        if (m.Name() == name) {
            if (m.IsPublic())
                result.push_back((cppyy_index_t)imeth);
        }
    }
    if (result.empty())
        return (cppyy_index_t*)0;
    cppyy_index_t* llresult = (cppyy_index_t*)malloc(sizeof(cppyy_index_t)*(result.size()+1));
    for (int i = 0; i < (int)result.size(); ++i) llresult[i] = result[i];
    llresult[result.size()] = -1;
    return llresult;
}

char* cppyy_method_name(cppyy_scope_t handle, cppyy_index_t method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    std::string name;
    if (m.IsConstructor())
        name = s.Name(Reflex::FINAL);   // to get proper name for templates
    else if (m.IsTemplateInstance()) {
        name = m.Name();
        std::string::size_type pos = name.find('<');
        name = name.substr(0, pos);     // strip template argument portion for overload
    } else
        name = m.Name();
    return cppstring_to_cstring(name);
}

char* cppyy_method_result_type(cppyy_scope_t handle, cppyy_index_t method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    if (m.IsConstructor())
        return cppstring_to_cstring("constructor");
    Reflex::Type rt = m.TypeOf().ReturnType();
    std::string name = rt.Name(Reflex::FINAL|Reflex::SCOPED|Reflex::QUALIFIED);
    return cppstring_to_cstring(name);
}

int cppyy_method_num_args(cppyy_scope_t handle, cppyy_index_t method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    return m.FunctionParameterSize();
}

int cppyy_method_req_args(cppyy_scope_t handle, cppyy_index_t method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    return m.FunctionParameterSize(true);
}

char* cppyy_method_arg_type(cppyy_scope_t handle, cppyy_index_t method_index, int arg_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    Reflex::Type at = m.TypeOf().FunctionParameterAt(arg_index);
    std::string name = at.Name(Reflex::FINAL|Reflex::SCOPED|Reflex::QUALIFIED);
    return cppstring_to_cstring(name);
}

char* cppyy_method_arg_default(cppyy_scope_t handle, cppyy_index_t method_index, int arg_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    std::string dflt = m.FunctionParameterDefaultAt(arg_index);
    return cppstring_to_cstring(dflt);
}

char* cppyy_method_signature(cppyy_scope_t handle, cppyy_index_t method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    Reflex::Type mt = m.TypeOf();
    std::ostringstream sig;
    if (!m.IsConstructor())
        sig << mt.ReturnType().Name() << " ";
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


int cppyy_method_is_template(cppyy_scope_t handle, cppyy_index_t method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    return m.IsTemplateInstance();
}

int cppyy_method_num_template_args(cppyy_scope_t handle, cppyy_index_t method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    assert(m.IsTemplateInstance());
    return m.TemplateArgumentSize();
}

char* cppyy_method_template_arg_name(
        cppyy_scope_t handle, cppyy_index_t method_index, cppyy_index_t iarg) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    assert(m.IsTemplateInstance());
    return cppstring_to_cstring(
       m.TemplateArgumentAt(iarg).Name(Reflex::SCOPED|Reflex::QUALIFIED));
}


cppyy_method_t cppyy_get_method(cppyy_scope_t handle, cppyy_index_t method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    return (cppyy_method_t)m.Stubfunction();
}

cppyy_index_t cppyy_get_global_operator(cppyy_scope_t scope, cppyy_scope_t lc, cppyy_scope_t rc, const char* op) {
    Reflex::Type lct = type_from_handle(lc);
    Reflex::Type rct = type_from_handle(rc);
    Reflex::Scope nss = scope_from_handle(scope);

    if (!lct || !rct || !nss) 
        return (cppyy_index_t)-1;  // (void*)-1 is in kernel space, so invalid as a method handle

    std::string lcname = lct.Name(Reflex::SCOPED|Reflex::FINAL);
    std::string rcname = rct.Name(Reflex::SCOPED|Reflex::FINAL);

    std::string opname = "operator";
    opname += op;

    for (int idx = 0; idx < (int)nss.FunctionMemberSize(); ++idx) {
        Reflex::Member m = nss.FunctionMemberAt(idx);
        if (m.FunctionParameterSize() != 2)
            continue;

        if (m.Name() == opname) {
            Reflex::Type mt = m.TypeOf();
            if (lcname == mt.FunctionParameterAt(0).Name(Reflex::SCOPED|Reflex::FINAL) &&
                rcname == mt.FunctionParameterAt(1).Name(Reflex::SCOPED|Reflex::FINAL)) {
                return (cppyy_index_t)idx;
            }
        }
    }

    return (cppyy_index_t)-1;  
}


/* method properties -----------------------------------------------------  */
int cppyy_is_constructor(cppyy_type_t handle, cppyy_index_t method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    return m.IsConstructor();
}

int cppyy_is_staticmethod(cppyy_type_t handle, cppyy_index_t method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    return m.IsStatic();
}


/* data member reflection information ------------------------------------- */
int cppyy_num_datamembers(cppyy_scope_t handle) {
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

char* cppyy_datamember_name(cppyy_scope_t handle, int datamember_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.DataMemberAt(datamember_index);
    std::string name = m.Name();
    return cppstring_to_cstring(name);
}

char* cppyy_datamember_type(cppyy_scope_t handle, int datamember_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.DataMemberAt(datamember_index);
    std::string name = m.TypeOf().Name(Reflex::FINAL|Reflex::SCOPED|Reflex::QUALIFIED);
    return cppstring_to_cstring(name);
}

ptrdiff_t cppyy_datamember_offset(cppyy_scope_t handle, int datamember_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.DataMemberAt(datamember_index);
    if (m.IsArtificial() && m.TypeOf().IsEnum())
        return (ptrdiff_t)&m.InterpreterOffset();
    return (ptrdiff_t)m.Offset();
}

int cppyy_datamember_index(cppyy_scope_t handle, const char* name) {
    Reflex::Scope s = scope_from_handle(handle);
    // the following appears dumb, but the internal storage for Reflex is an
    // unsorted std::vector anyway, so there's no gain to be had in using the
    // Scope::DataMemberByName() function (which returns Member, not an index)
    int num_dm = cppyy_num_datamembers(handle);
    for (int idm = 0; idm < num_dm; ++idm) {
        Reflex::Member m = s.DataMemberAt(idm);
        if (m.Name() == name || m.Name(Reflex::FINAL) == name) {
            if (m.IsPublic())
                return idm;
            return -1;
        }
    }
    return -1;
}


/* data member properties ------------------------------------------------  */
int cppyy_is_publicdata(cppyy_scope_t handle, int datamember_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.DataMemberAt(datamember_index);
    return m.IsPublic();
}

int cppyy_is_staticdata(cppyy_scope_t handle, int datamember_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.DataMemberAt(datamember_index);
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
    void* arena = new char[sizeof(std::string)];
    new (arena) std::string(str);
    return (cppyy_object_t)arena;
}

cppyy_object_t cppyy_stdstring2stdstring(cppyy_object_t ptr) {
    void* arena = new char[sizeof(std::string)];
    new (arena) std::string(*(std::string*)ptr);
    return (cppyy_object_t)arena;
}
