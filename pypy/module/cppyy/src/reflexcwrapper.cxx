#include "cppyy.h"
#include "reflexcwrapper.h"
#include <iostream>
#include <string>
#include <vector>


/* local helpers ---------------------------------------------------------- */
static inline char* cppstring_to_cstring( const std::string& name ) {
    char* name_char = (char*)malloc(name.size() + 1);
    strcpy(name_char, name.c_str());
    return name_char;
}


/* name to handle --------------------------------------------------------- */
cppyy_typehandle_t cppyy_get_typehandle(const char* class_name) {
   return Reflex::Type::ByName(class_name).Id();
}


/* memory management ------------------------------------------------------ */
void* cppyy_allocate(cppyy_typehandle_t handle) {
    return Reflex::Type((Reflex::TypeName*)handle).Allocate();
}

void cppyy_deallocate(cppyy_typehandle_t handle, cppyy_object_t instance) {
    Reflex::Type((Reflex::TypeName*)handle).Deallocate(instance);
}

void cppyy_destruct(cppyy_typehandle_t handle, cppyy_object_t self) {
    Reflex::Type t((Reflex::TypeName*)handle);
    t.Destruct(self, true);
}


/* method/function dispatching -------------------------------------------- */
void cppyy_call_v(cppyy_typehandle_t handle, int method_index,
                  cppyy_object_t self, int numargs, void* args[]) {
    std::vector<void*> arguments(args, args+numargs);
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    if (self) {
        Reflex::Object o(t, self);
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
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    if (self) {
        Reflex::Object o(t, self);
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
  else
    return 0;
}

cppyy_methptrgetter_t cppyy_get_methptr_getter(cppyy_typehandle_t handle, int method_index)
{
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    return get_methptr_getter(m);
}


/* type/class reflection information -------------------------------------- */
int cppyy_num_bases(cppyy_typehandle_t handle) {
    Reflex::Type t((Reflex::TypeName*)handle);
    return t.BaseSize();
}

char* cppyy_base_name(cppyy_typehandle_t handle, int base_index) {
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Base b = t.BaseAt(base_index);
    std::string name = b.Name(Reflex::FINAL|Reflex::SCOPED);
    return cppstring_to_cstring(name);
}

int cppyy_is_subtype(cppyy_typehandle_t h1, cppyy_typehandle_t h2) {
    if (h1 == h2)
        return 1;
    Reflex::Type t1((Reflex::TypeName*)h1);
    Reflex::Type t2((Reflex::TypeName*)h2);
    return (int)t2.HasBase(t1);
}


/* method/function reflection information --------------------------------- */
int cppyy_num_methods(cppyy_typehandle_t handle) {
    Reflex::Type t((Reflex::TypeName*)handle);
    // for (int i = 0; i < (int)t.FunctionMemberSize(); i++) {
    //     Reflex::Member m = t.FunctionMemberAt(i);
    //     std::cout << i << " " << m.Name() << std::endl;
    //     std::cout << "    " << "Stubfunction:  " << (void*)m.Stubfunction() << std::endl;
    //     std::cout << "    " << "MethPtrGetter: " << (void*)get_methptr_getter(m) << std::endl;
    //     for (int j = 0; j < (int)m.FunctionParameterSize(); j++) {
    //         Reflex::Type at = m.TypeOf().FunctionParameterAt(j);
    //         std::cout << "    " << j << " " << at.Name() << std::endl;
    //     }
    // }
    return t.FunctionMemberSize();
}

char* cppyy_method_name(cppyy_typehandle_t handle, int method_index) {
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    std::string name = m.Name();
    return cppstring_to_cstring(name);
}

char* cppyy_method_result_type(cppyy_typehandle_t handle, int method_index) {
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    Reflex::Type rt = m.TypeOf().ReturnType();
    std::string name = rt.Name(Reflex::FINAL|Reflex::SCOPED|Reflex::QUALIFIED);
    return cppstring_to_cstring(name);
}

int cppyy_method_num_args(cppyy_typehandle_t handle, int method_index) {
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    return m.FunctionParameterSize();
}

char* cppyy_method_arg_type(cppyy_typehandle_t handle, int method_index, int arg_index) {
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    Reflex::Type at = m.TypeOf().FunctionParameterAt(arg_index);
    std::string name = at.Name(Reflex::FINAL|Reflex::SCOPED|Reflex::QUALIFIED);
    return cppstring_to_cstring(name);
}


int cppyy_is_constructor(cppyy_typehandle_t handle, int method_index) {
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    return m.IsConstructor();
}

int cppyy_is_staticmethod(cppyy_typehandle_t handle, int method_index) {
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.FunctionMemberAt(method_index);
    return m.IsStatic();
}


/* data member reflection information ------------------------------------- */
int cppyy_num_data_members(cppyy_typehandle_t handle) {
    Reflex::Type t((Reflex::TypeName*)handle);
    return t.DataMemberSize();
}

char* cppyy_data_member_name(cppyy_typehandle_t handle, int data_member_index) {
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.DataMemberAt(data_member_index);
    std::string name = m.Name();
    char* name_char = (char*)malloc(name.size() + 1);
    strcpy(name_char, name.c_str());
    return name_char;
}

char* cppyy_data_member_type(cppyy_typehandle_t handle, int data_member_index) {
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.DataMemberAt(data_member_index);
    std::string name = m.TypeOf().Name(Reflex::FINAL|Reflex::SCOPED|Reflex::QUALIFIED);
    char* name_char = (char*)malloc(name.size() + 1);
    strcpy(name_char, name.c_str());
    return name_char;
}

size_t cppyy_data_member_offset(cppyy_typehandle_t handle, int data_member_index) {
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.DataMemberAt(data_member_index);
    return m.Offset();
}


int cppyy_is_staticdata(cppyy_typehandle_t handle, int data_member_index) {
    Reflex::Type t((Reflex::TypeName*)handle);
    Reflex::Member m = t.DataMemberAt(data_member_index);
    return m.IsStatic();
}


/* misc helper ------------------------------------------------------------ */
void cppyy_free(void* ptr) {
    free(ptr);
}
