#include "cppyy.h"
#include "reflexcwrapper.h"
#include <iostream>
#include <string>
#include <utility>
#include <vector>


/* local helpers ---------------------------------------------------------- */
static inline char* cppstring_to_cstring(const std::string& name) {
    char* name_char = (char*)malloc(name.size() + 1);
    strcpy(name_char, name.c_str());
    return name_char;
}

static inline Reflex::Scope scope_from_handle(cppyy_typehandle_t handle) {
    return Reflex::Scope((Reflex::ScopeName*)handle);
}

static inline Reflex::Type type_from_handle(cppyy_typehandle_t handle) {
    return Reflex::Scope((Reflex::ScopeName*)handle);
}


/* name to handle --------------------------------------------------------- */
cppyy_typehandle_t cppyy_get_typehandle(const char* class_name) {
    Reflex::Scope s = Reflex::Scope::ByName(class_name);
    return s.Id();
}

cppyy_typehandle_t cppyy_get_templatehandle(const char* template_name) {
   Reflex::TypeTemplate tt = Reflex::TypeTemplate::ByName(template_name);
   return tt.Id();
}


/* memory management ------------------------------------------------------ */
void* cppyy_allocate(cppyy_typehandle_t handle) {
    Reflex::Type t = type_from_handle(handle);
    return t.Allocate();
}

void cppyy_deallocate(cppyy_typehandle_t handle, cppyy_object_t instance) {
    Reflex::Type t = type_from_handle(handle);
    t.Deallocate(instance);
}

void cppyy_destruct(cppyy_typehandle_t handle, cppyy_object_t self) {
    Reflex::Type t = type_from_handle(handle);
    t.Destruct(self, true);
}


/* method/function dispatching -------------------------------------------- */
void cppyy_call_v(cppyy_typehandle_t handle, int method_index,
                  cppyy_object_t self, int numargs, void* args[]) {
    std::vector<void*> arguments(args, args+numargs);
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    if (self) {
        Reflex::Object o((Reflex::Type)s, self);
        m.Invoke(o, 0, arguments);
    } else {
        m.Invoke(0, arguments);
    }
}

template<typename T>
static inline T cppyy_call_T(cppyy_typehandle_t handle, int method_index,
                             cppyy_object_t self, int numargs, void* args[]) {
    T result;
    std::vector<void*> arguments(args, args+numargs);
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    if (self) {
        Reflex::Object o((Reflex::Type)s, self);
        m.Invoke(o, result, arguments);
    } else {
        m.Invoke(result, arguments);
    }
    return result;
}

int cppyy_call_b(cppyy_typehandle_t handle, int method_index,
                  cppyy_object_t self, int numargs, void* args[]) {
    return (int)cppyy_call_T<bool>(handle, method_index, self, numargs, args);
}

char cppyy_call_c(cppyy_typehandle_t handle, int method_index,
                 cppyy_object_t self, int numargs, void* args[]) {
    return cppyy_call_T<char>(handle, method_index, self, numargs, args);
}

short cppyy_call_h(cppyy_typehandle_t handle, int method_index,
                   cppyy_object_t self, int numargs, void* args[]) {
    return cppyy_call_T<short>(handle, method_index, self, numargs, args);
}

long cppyy_call_l(cppyy_typehandle_t handle, int method_index,
                  cppyy_object_t self, int numargs, void* args[]) {
    return cppyy_call_T<long>(handle, method_index, self, numargs, args);
}

double cppyy_call_f(cppyy_typehandle_t handle, int method_index,
                    cppyy_object_t self, int numargs, void* args[]) {
    return cppyy_call_T<float>(handle, method_index, self, numargs, args);
}

double cppyy_call_d(cppyy_typehandle_t handle, int method_index,
                    cppyy_object_t self, int numargs, void* args[]) {
    return cppyy_call_T<double>(handle, method_index, self, numargs, args);
}   


static cppyy_methptrgetter_t get_methptr_getter(Reflex::Member m) {
    Reflex::PropertyList plist = m.Properties();
    if (plist.HasProperty("MethPtrGetter")) {
        Reflex::Any& value = plist.PropertyValue("MethPtrGetter");
        return (cppyy_methptrgetter_t)Reflex::any_cast<void*>(value);
    }
    return 0;
}

cppyy_methptrgetter_t cppyy_get_methptr_getter(cppyy_typehandle_t handle, int method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    return get_methptr_getter(m);
}


/* scope reflection information ------------------------------------------- */
int cppyy_is_namespace(cppyy_typehandle_t handle) {
    Reflex::Scope s = scope_from_handle(handle);
    return s.IsNamespace();
}


/* type/class reflection information -------------------------------------- */
char* cppyy_final_name(cppyy_typehandle_t handle) {
    Reflex::Scope s = scope_from_handle(handle);
    std::string name = s.Name(Reflex::FINAL);
    return cppstring_to_cstring(name);
}

int cppyy_num_bases(cppyy_typehandle_t handle) {
    Reflex::Type t = type_from_handle(handle);
    return t.BaseSize();
}

char* cppyy_base_name(cppyy_typehandle_t handle, int base_index) {
    Reflex::Type t = type_from_handle(handle);
    Reflex::Base b = t.BaseAt(base_index);
    std::string name = b.Name(Reflex::FINAL|Reflex::SCOPED);
    return cppstring_to_cstring(name);
}

int cppyy_is_subtype(cppyy_typehandle_t h1, cppyy_typehandle_t h2) {
    if (h1 == h2)
        return 1;
    Reflex::Type t1 = type_from_handle(h1);
    Reflex::Type t2 = type_from_handle(h2);
    return (int)t2.HasBase(t1);
}


/* method/function reflection information --------------------------------- */
int cppyy_num_methods(cppyy_typehandle_t handle) {
    Reflex::Scope s = scope_from_handle(handle);
    return s.FunctionMemberSize();
}

char* cppyy_method_name(cppyy_typehandle_t handle, int method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    std::string name;
    if (m.IsConstructor())
       name = s.Name(Reflex::FINAL);    // to get proper name for templates
    else
       name = m.Name();
    return cppstring_to_cstring(name);
}

char* cppyy_method_result_type(cppyy_typehandle_t handle, int method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    Reflex::Type rt = m.TypeOf().ReturnType();
    std::string name = rt.Name(Reflex::FINAL|Reflex::SCOPED|Reflex::QUALIFIED);
    return cppstring_to_cstring(name);
}

int cppyy_method_num_args(cppyy_typehandle_t handle, int method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    return m.FunctionParameterSize();
}

char* cppyy_method_arg_type(cppyy_typehandle_t handle, int method_index, int arg_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    Reflex::Type at = m.TypeOf().FunctionParameterAt(arg_index);
    std::string name = at.Name(Reflex::FINAL|Reflex::SCOPED|Reflex::QUALIFIED);
    return cppstring_to_cstring(name);
}


int cppyy_is_constructor(cppyy_typehandle_t handle, int method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    return m.IsConstructor();
}

int cppyy_is_staticmethod(cppyy_typehandle_t handle, int method_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.FunctionMemberAt(method_index);
    return m.IsStatic();
}


/* data member reflection information ------------------------------------- */
int cppyy_num_data_members(cppyy_typehandle_t handle) {
    Reflex::Scope s = scope_from_handle(handle);
    return s.DataMemberSize(Reflex::INHERITEDMEMBERS_ALSO);
}

char* cppyy_data_member_name(cppyy_typehandle_t handle, int data_member_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.DataMemberAt(data_member_index, Reflex::INHERITEDMEMBERS_ALSO);
    std::string name = m.Name();
    return cppstring_to_cstring(name);
}

char* cppyy_data_member_type(cppyy_typehandle_t handle, int data_member_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.DataMemberAt(data_member_index, Reflex::INHERITEDMEMBERS_ALSO);
    std::string name = m.TypeOf().Name(Reflex::FINAL|Reflex::SCOPED|Reflex::QUALIFIED);
    return cppstring_to_cstring(name);
}

static void* fgFakeObject  = 0;
static void* fgFakeAddress = &fgFakeObject;

size_t cppyy_data_member_offset(cppyy_typehandle_t handle, int data_member_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.DataMemberAt(data_member_index, Reflex::INHERITEDMEMBERS_ALSO);

    if (s != m.DeclaringScope()) {
        // in case this data member is part of a base class, the offset is complicated
        // when dealing with virtual inheritance and only (reasonably) well-defined with a
        // Reflex internal base table, that contains all offsets within the full hierarchy
        Reflex::Member getbases = s.FunctionMemberByName(
            "__getBasesTable", Reflex::Type(), 0, Reflex::INHERITEDMEMBERS_NO, Reflex::DELAYEDLOAD_OFF);
        if (getbases) {
            typedef std::vector<std::pair<Reflex::Base, int> > Bases_t;
            Bases_t* bases;
            Reflex::Object bases_holder(Reflex::Type::ByTypeInfo(typeid(Bases_t)), &bases);
            getbases.Invoke(&bases_holder);

            Reflex::Type d = m.DeclaringType();

            for (Bases_t::iterator ibase = bases->begin(); ibase != bases->end(); ++ibase) {
                if (ibase->first.ToType() == d) {
                    if (d.IsVirtual()) {
                        Reflex::Type t = type_from_handle(handle);
                        Reflex::Object o = t.Construct();
                        size_t offset = ibase->first.Offset(o.Address()) + m.Offset();
                        o.Destruct();
                        return offset;
                    } else
                        return ibase->first.Offset(0);
                }
            }

            // contrary to typical invoke()s, the result of the internal getbases function
            // is a pointer to a function static, so no delete
        }
    }

    return m.Offset();
}


int cppyy_is_staticdata(cppyy_typehandle_t handle, int data_member_index) {
    Reflex::Scope s = scope_from_handle(handle);
    Reflex::Member m = s.DataMemberAt(data_member_index, Reflex::INHERITEDMEMBERS_ALSO);
    return m.IsStatic();
}


/* misc helper ------------------------------------------------------------ */
void cppyy_free(void* ptr) {
    free(ptr);
}
