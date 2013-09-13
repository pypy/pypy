#include "cppyy.h"
#include "cintcwrapper.h"

#include "TROOT.h"
#include "TError.h"
#include "TList.h"
#include "TSystem.h"

#include "TApplication.h"
#include "TInterpreter.h"
#include "TVirtualMutex.h"
#include "Getline.h"

#include "TBaseClass.h"
#include "TClass.h"
#include "TClassEdit.h"
#include "TClassRef.h"
#include "TClassTable.h"
#include "TDataMember.h"
#include "TFunction.h"
#include "TGlobal.h"
#include "TMethod.h"
#include "TMethodArg.h"

// for pythonization
#include "TTree.h"
#include "TBranch.h"
#include "TString.h"

#include "Api.h"

#include <assert.h>
#include <string.h>
#include <map>
#include <sstream>
#include <string>
#include <utility>


/* ROOT/CINT internals --------------------------------------------------- */
extern long G__store_struct_offset;
extern "C" void G__LockCriticalSection();
extern "C" void G__UnlockCriticalSection();

#define G__SETMEMFUNCENV      (long)0x7fff0035
#define G__NOP                (long)0x7fff00ff

namespace {

class Cppyy_OpenedTClass : public TDictionary {
public:
    mutable TObjArray* fStreamerInfo;    //Array of TVirtualStreamerInfo
    mutable std::map<std::string, TObjArray*>* fConversionStreamerInfo; //Array of the streamer infos derived from another class.
    TList*             fRealData;       //linked list for persistent members including base classes
    TList*             fBase;           //linked list for base classes
    TList*             fData;           //linked list for data members
    TList*             fMethod;         //linked list for methods
    TList*             fAllPubData;     //all public data members (including from base classes)
    TList*             fAllPubMethod;   //all public methods (including from base classes)
};

// memory regulation (cppyy_recursive_remove is generated a la cpyext capi calls)
extern "C" void cppyy_recursive_remove(void*);

// TFN callback helper (generated a la cpyext capi calls)
extern "C" double cppyy_tfn_callback(long, int, double*, double*);

class Cppyy_MemoryRegulator : public TObject {
public:
    virtual void RecursiveRemove(TObject* object) {
        cppyy_recursive_remove((void*)object);
    }
};

} // unnamed namespace


/* data for life time management ------------------------------------------ */
#define GLOBAL_HANDLE 1l

typedef std::vector<TClassRef> ClassRefs_t;
static ClassRefs_t g_classrefs(1);

typedef std::map<std::string, ClassRefs_t::size_type> ClassRefIndices_t;
static ClassRefIndices_t g_classref_indices;

typedef std::vector<TFunction> GlobalFuncs_t;
static GlobalFuncs_t g_globalfuncs;

typedef std::vector<TGlobal> GlobalVars_t;
static GlobalVars_t g_globalvars;

typedef std::vector<G__MethodInfo> InterpretedFuncs_t;
static InterpretedFuncs_t g_interpreted;


/* initialization of the ROOT system (debatable ... ) --------------------- */
namespace {

static Cppyy_MemoryRegulator s_memreg;

class TCppyyApplication : public TApplication {
public:
    TCppyyApplication(const char* acn, Int_t* argc, char** argv, Bool_t do_load = kTRUE)
           : TApplication(acn, argc, argv) {

        // Explicitly load libMathCore as CINT will not auto load it when using
        // one of its globals. Once moved to Cling, which should work correctly,
        // we can remove this statement.
        gSystem->Load("libMathCore");

        if (do_load) {
            // follow TRint to minimize differences with CINT
            ProcessLine("#include <iostream>", kTRUE);
            ProcessLine("#include <_string>",  kTRUE); // for std::string iostream.
            ProcessLine("#include <DllImport.h>", kTRUE);// Defined R__EXTERN
            ProcessLine("#include <vector>",   kTRUE); // needed because they're used within the
            ProcessLine("#include <pair>",     kTRUE); //  core ROOT dicts and CINT won't be able
                                                       //  to properly unload these files
        }

        // save current interpreter context
        gInterpreter->SaveContext();
        gInterpreter->SaveGlobalsContext();

        // prevent crashes on accessing history
        Gl_histinit((char*)"-");

        // prevent ROOT from exiting python
        SetReturnFromRun(kTRUE);

        // enable auto-loader
        gInterpreter->EnableAutoLoading();

        // enable memory regulation
        gROOT->GetListOfCleanups()->Add(&s_memreg);
    }
};

static const char* appname = "PyPyROOT";

class ApplicationStarter {
public:
    ApplicationStarter() {
        // setup dummy holders for global and std namespaces
        assert(g_classrefs.size() == (ClassRefs_t::size_type)GLOBAL_HANDLE);
        g_classref_indices[""] = (ClassRefs_t::size_type)GLOBAL_HANDLE;
        g_classrefs.push_back(TClassRef(""));
        g_classref_indices["std"] = g_classrefs.size();
        g_classrefs.push_back(TClassRef(""));    // CINT ignores std
        g_classref_indices["::std"] = g_classrefs.size();
        g_classrefs.push_back(TClassRef(""));    // id.
 
        // an offset for the interpreted methods
        g_interpreted.push_back(G__MethodInfo());

        // actual application init, if necessary
        if (!gApplication) {
            int argc = 1;
            char* argv[1]; argv[0] = (char*)appname;
            gApplication = new TCppyyApplication(appname, &argc, argv, kTRUE);
            if (!gProgName)                  // should have been set by TApplication
                gSystem->SetProgname(appname);
        }

        // program name should've been set by TApplication; just in case ...
        if (!gProgName) {
            gSystem->SetProgname(appname);
        }
    }
} _applicationStarter;

} // unnamed namespace


/* local helpers ---------------------------------------------------------- */
static inline const std::string resolve_typedef(const std::string& tname) {
    G__TypeInfo ti(tname.c_str());
    if (!ti.IsValid())
        return tname;
    return TClassEdit::ShortType(TClassEdit::CleanType(ti.TrueName(), 1).c_str(), 3);
}

static inline char* cppstring_to_cstring(const std::string& name) {
    char* name_char = (char*)malloc(name.size() + 1);
    strcpy(name_char, name.c_str());
    return name_char;
}

static inline char* type_cppstring_to_cstring(const std::string& tname) {
    G__TypeInfo ti(tname.c_str());
    std::string true_name = ti.IsValid() ? ti.TrueName() : tname;
    return cppstring_to_cstring(true_name);
}

static inline TClassRef& type_from_handle(cppyy_type_t handle) {
    assert((ClassRefs_t::size_type)handle < g_classrefs.size());
    return g_classrefs[(ClassRefs_t::size_type)handle];
}

static inline TFunction* type_get_method(cppyy_type_t handle, cppyy_index_t idx) {
    TClassRef& cr = type_from_handle(handle);
    if (cr.GetClass())
        return (TFunction*)cr->GetListOfMethods()->At(idx);
    return (TFunction*)idx;
}

static inline void fixup_args(G__param* libp) {
    for (int i = 0; i < libp->paran; ++i) {
        libp->para[i].ref = libp->para[i].obj.i;
        const char partype = libp->para[i].type;
        switch (partype) {
        case 'p': {
            libp->para[i].obj.i = (long)&libp->para[i].ref;
            break;
        }
        case 'r': {
            libp->para[i].ref = (long)&libp->para[i].obj.i;
            break;
        }
        case 'f': {
            float val = libp->para[i].obj.fl;
            libp->para[i].obj.d = val;
            break;
        }
        case 'F': {
            libp->para[i].ref = (long)&libp->para[i].obj.i;
            libp->para[i].type = 'f';
            break;
        }
        case 'D': {
            libp->para[i].ref = (long)&libp->para[i].obj.i;
            libp->para[i].type = 'd';
            break;
        }
        }
    }
}


/* name to opaque C++ scope representation -------------------------------- */
int cppyy_num_scopes(cppyy_scope_t handle) {
    TClassRef& cr = type_from_handle(handle);
    if (cr.GetClass()) {
        /* not supported as CINT does not store classes hierarchically */
        return 0;
    }
    return gClassTable->Classes();
}

char* cppyy_scope_name(cppyy_scope_t handle, int iscope) {
    TClassRef& cr = type_from_handle(handle);
    if (cr.GetClass()) {
        /* not supported as CINT does not store classes hierarchically */
        assert(!"scope name lookup not supported on inner scopes");
        return 0;
    }
    std::string name = gClassTable->At(iscope);
    if (name.find("::") == std::string::npos)
        return cppstring_to_cstring(name);
    return cppstring_to_cstring("");
}

char* cppyy_resolve_name(const char* cppitem_name) {
    std::string tname = cppitem_name;

    // global namespace?
    if (tname.empty())
        return cppstring_to_cstring(cppitem_name);

    // special care needed for builtin arrays
    std::string::size_type pos = tname.rfind("[");
    G__TypeInfo ti(tname.substr(0, pos).c_str());

    // if invalid (most likely unknown), simply return old name
    if (!ti.IsValid())
        return cppstring_to_cstring(cppitem_name);

    // special case treatment of enum types as unsigned int (CINTism)
    if (ti.Property() & G__BIT_ISENUM)
        return cppstring_to_cstring("unsigned int");

    // actual typedef resolution; add back array declaration portion, if needed
    std::string rt = ti.TrueName();

    // builtin STL types have fake typedefs :/
    G__TypeInfo ti_test(rt.c_str());
    if (!ti_test.IsValid())
        return cppstring_to_cstring(cppitem_name);

    if (pos != std::string::npos)
        rt += tname.substr(pos, std::string::npos);
    return cppstring_to_cstring(rt);
}

cppyy_scope_t cppyy_get_scope(const char* scope_name) {
    // CINT still has trouble with std:: sometimes ... 
    if (strncmp(scope_name, "std::", 5) == 0)
        scope_name = &scope_name[5];

    ClassRefIndices_t::iterator icr = g_classref_indices.find(scope_name);
    if (icr != g_classref_indices.end())
        return (cppyy_type_t)icr->second;

    if (strcmp(scope_name, "#define") == 0)
        return (cppyy_type_t)NULL;

    // use TClass directly, to enable auto-loading
    TClassRef cr(TClass::GetClass(scope_name, kTRUE, kTRUE));
    if (!cr.GetClass())
        return (cppyy_type_t)NULL;

    if (!cr->GetClassInfo())
        return (cppyy_type_t)NULL;

    if (!G__TypeInfo(scope_name).IsValid())
        return (cppyy_type_t)NULL;

    ClassRefs_t::size_type sz = g_classrefs.size();
    g_classref_indices[scope_name] = sz;
    g_classrefs.push_back(TClassRef(scope_name));
    return (cppyy_scope_t)sz;
}

cppyy_type_t cppyy_get_template(const char* template_name) {
    ClassRefIndices_t::iterator icr = g_classref_indices.find(template_name);
    if (icr != g_classref_indices.end())
        return (cppyy_type_t)icr->second;

    if (!G__defined_templateclass((char*)template_name))
        return (cppyy_type_t)NULL;

    // #include for specific, pre-compiled STL classes
    if (strcmp(template_name, "std::map") == 0)
        gROOT->ProcessLine("#include <map>");

    // the following yields a dummy TClassRef, but its name can be queried
    ClassRefs_t::size_type sz = g_classrefs.size();
    g_classref_indices[template_name] = sz;
    g_classrefs.push_back(TClassRef(template_name));
    return (cppyy_type_t)sz;
}

cppyy_type_t cppyy_actual_class(cppyy_type_t klass, cppyy_object_t obj) {
    TClassRef& cr = type_from_handle(klass);
    TClass* clActual = cr->GetActualClass( (void*)obj );
    if (clActual && clActual != cr.GetClass()) {
        // TODO: lookup through name should not be needed
        return (cppyy_type_t)cppyy_get_scope(clActual->GetName());
    }
    return klass;
}


/* memory management ------------------------------------------------------ */
cppyy_object_t cppyy_allocate(cppyy_type_t handle) {
    TClassRef& cr = type_from_handle(handle);
    return (cppyy_object_t)malloc(cr->Size());
}

void cppyy_deallocate(cppyy_type_t /*handle*/, cppyy_object_t instance) {
    free((void*)instance);
}

void cppyy_destruct(cppyy_type_t handle, cppyy_object_t self) {
    TClassRef& cr = type_from_handle(handle);
    cr->Destructor((void*)self, true);
}


/* method/function dispatching -------------------------------------------- */
static inline G__value cppyy_call_T(cppyy_method_t method,
        cppyy_object_t self, int nargs, void* args) {

    R__LOCKGUARD2(gCINTMutex);

    G__param* libp = (G__param*)((char*)args - offsetof(G__param, para));
    assert(libp->paran == nargs);
    fixup_args(libp);

    if ((InterpretedFuncs_t::size_type)method < g_interpreted.size()) {
    // the idea here is that all these low values are invalid memory addresses,
    // allowing the reuse of method to index the stored bytecodes
        G__CallFunc callf;
        callf.SetFunc(g_interpreted[(size_t)method]);
        G__param p;      // G__param has fixed size; libp is sized to nargs
        for (int i =0; i<nargs; ++i)
            p.para[i] = libp->para[i];
        p.paran = nargs;
        callf.SetArgs(p);     // will copy p yet again
        return callf.Execute((void*)self);
    }

    G__InterfaceMethod meth = (G__InterfaceMethod)method;

    G__value result;
    G__setnull(&result);

    G__LockCriticalSection();      // CINT-level lock, is recursive
    G__settemplevel(1);

    long index = (long)&method;
    G__CurrentCall(G__SETMEMFUNCENV, 0, &index);

    // TODO: access to store_struct_offset won't work on Windows
    long store_struct_offset = G__store_struct_offset;
    if (self)
        G__store_struct_offset = (long)self;

    meth(&result, (char*)0, libp, 0);
    if (self)
        G__store_struct_offset = store_struct_offset;

    if (G__get_return(0) > G__RETURN_NORMAL)
        G__security_recover(0);    // 0 ensures silence

    G__CurrentCall(G__NOP, 0, 0);
    G__settemplevel(-1);
    G__UnlockCriticalSection();

    return result;
}

void cppyy_call_v(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    cppyy_call_T(method, self, nargs, args);
}

unsigned char cppyy_call_b(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    G__value result = cppyy_call_T(method, self, nargs, args);
    return (unsigned char)(bool)G__int(result);
}

char cppyy_call_c(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    G__value result = cppyy_call_T(method, self, nargs, args);
    return (char)G__int(result);
}

short cppyy_call_h(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    G__value result = cppyy_call_T(method, self, nargs, args);
    return (short)G__int(result);
}

int cppyy_call_i(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    G__value result = cppyy_call_T(method, self, nargs, args);
    return (int)G__int(result);
}

long cppyy_call_l(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    G__value result = cppyy_call_T(method, self, nargs, args);
    return G__int(result);
}

long long cppyy_call_ll(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    G__value result = cppyy_call_T(method, self, nargs, args);
    return G__Longlong(result);
}

float cppyy_call_f(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    G__value result = cppyy_call_T(method, self, nargs, args);
    return (float)G__double(result);
}

double cppyy_call_d(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    G__value result = cppyy_call_T(method, self, nargs, args);
    return G__double(result);
}

void* cppyy_call_r(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    G__value result = cppyy_call_T(method, self, nargs, args);
    return (void*)result.ref;
}

char* cppyy_call_s(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    G__value result = cppyy_call_T(method, self, nargs, args);
    G__pop_tempobject_nodel();
    if (result.ref && *(long*)result.ref) {
        char* charp = cppstring_to_cstring(*(std::string*)result.ref);
        delete (std::string*)result.ref;
        return charp;
    }
    return cppstring_to_cstring("");
}

cppyy_object_t cppyy_constructor(cppyy_method_t method, cppyy_type_t handle, int nargs, void* args) {
    cppyy_object_t self = (cppyy_object_t)NULL;
    if ((InterpretedFuncs_t::size_type)method >= g_interpreted.size()) {
        G__setgvp((long)G__PVOID);
        self = (cppyy_object_t)cppyy_call_l(method, (cppyy_object_t)NULL, nargs, args);
    } else {
    // for macro's/interpreted classes
        self = cppyy_allocate(handle);
        G__setgvp((long)self);
        cppyy_call_T(method, self, nargs, args);
    }
    G__setgvp((long)G__PVOID);
    return self;
}

cppyy_object_t cppyy_call_o(cppyy_type_t method, cppyy_object_t self, int nargs, void* args,
                  cppyy_type_t /*result_type*/ ) {
    G__value result = cppyy_call_T(method, self, nargs, args);
    G__pop_tempobject_nodel();
    return G__int(result);
}

cppyy_methptrgetter_t cppyy_get_methptr_getter(cppyy_type_t /*handle*/, cppyy_index_t /*idx*/) {
    return (cppyy_methptrgetter_t)NULL;
}


/* handling of function argument buffer ----------------------------------- */
void* cppyy_allocate_function_args(size_t nargs) {
    assert(sizeof(CPPYY_G__value) == sizeof(G__value));
    G__param* libp = (G__param*)malloc(
        offsetof(G__param, para) + nargs*sizeof(CPPYY_G__value));
    libp->paran = (int)nargs;
    for (size_t i = 0; i < nargs; ++i)
        libp->para[i].type = 'l';
    return (void*)libp->para;
}

void cppyy_deallocate_function_args(void* args) {
    free((char*)args - offsetof(G__param, para));
}

size_t cppyy_function_arg_sizeof() {
    return sizeof(CPPYY_G__value);
}

size_t cppyy_function_arg_typeoffset() {
    return offsetof(CPPYY_G__value, type);
}


/* scope reflection information ------------------------------------------- */
int cppyy_is_namespace(cppyy_scope_t handle) {
    TClassRef& cr = type_from_handle(handle);
    if (cr.GetClass() && cr->GetClassInfo())
        return cr->Property() & G__BIT_ISNAMESPACE;
    if (strcmp(cr.GetClassName(), "") == 0)
        return true;
    return false;
}

int cppyy_is_enum(const char* type_name) {
    G__TypeInfo ti(type_name);
    return (ti.Property() & G__BIT_ISENUM);
}


/* type/class reflection information -------------------------------------- */
char* cppyy_final_name(cppyy_type_t handle) {
    TClassRef& cr = type_from_handle(handle);
    if (cr.GetClass() && cr->GetClassInfo()) {
        std::string true_name = G__TypeInfo(cr->GetName()).TrueName();
        std::string::size_type pos = true_name.rfind("::");
        if (pos != std::string::npos)
            return cppstring_to_cstring(true_name.substr(pos+2, std::string::npos));
        return cppstring_to_cstring(true_name);
    }
    return cppstring_to_cstring(cr.GetClassName());
}

char* cppyy_scoped_final_name(cppyy_type_t handle) {
    TClassRef& cr = type_from_handle(handle);
    if (cr.GetClass() && cr->GetClassInfo()) {
        std::string true_name = G__TypeInfo(cr->GetName()).TrueName();
        return cppstring_to_cstring(true_name);
    }
    return cppstring_to_cstring(cr.GetClassName());
}

int cppyy_has_complex_hierarchy(cppyy_type_t handle) {
// as long as no fast path is supported for CINT, calculating offsets (which
// are cached by the JIT) is not going to hurt 
    return 1;
}

int cppyy_num_bases(cppyy_type_t handle) {
    TClassRef& cr = type_from_handle(handle);
    if (cr.GetClass() && cr->GetListOfBases() != 0)
        return cr->GetListOfBases()->GetSize();
    return 0;
}

char* cppyy_base_name(cppyy_type_t handle, int base_index) {
    TClassRef& cr = type_from_handle(handle);
    TBaseClass* b = (TBaseClass*)cr->GetListOfBases()->At(base_index);
    return type_cppstring_to_cstring(b->GetName());
}

int cppyy_is_subtype(cppyy_type_t derived_handle, cppyy_type_t base_handle) {
    TClassRef& derived_type = type_from_handle(derived_handle);
    TClassRef& base_type = type_from_handle(base_handle);
    return derived_type->GetBaseClass(base_type) != 0;
}

size_t cppyy_base_offset(cppyy_type_t derived_handle, cppyy_type_t base_handle,
                       cppyy_object_t address, int /* direction */) {
    // WARNING: CINT can not handle actual dynamic casts!
    TClassRef& derived_type = type_from_handle(derived_handle);
    TClassRef& base_type = type_from_handle(base_handle);

    long offset = 0;

    if (derived_type && base_type) {
        G__ClassInfo* base_ci    = (G__ClassInfo*)base_type->GetClassInfo();
        G__ClassInfo* derived_ci = (G__ClassInfo*)derived_type->GetClassInfo();

        if (base_ci && derived_ci) {
#ifdef WIN32
            // Windows cannot cast-to-derived for virtual inheritance
            // with CINT's (or Reflex's) interfaces.
            long baseprop = derived_ci->IsBase(*base_ci);
            if (!baseprop || (baseprop & G__BIT_ISVIRTUALBASE))
                offset = derived_type->GetBaseClassOffset(base_type);
            else
#endif
                offset = G__isanybase(base_ci->Tagnum(), derived_ci->Tagnum(), (long)address);
         } else {
             offset = derived_type->GetBaseClassOffset(base_type);
         }
    }

    return (size_t) offset;   // may be negative (will roll over)
}


/* method/function reflection information --------------------------------- */
int cppyy_num_methods(cppyy_scope_t handle) {
    TClassRef& cr = type_from_handle(handle);
    if (cr.GetClass() && cr->GetListOfMethods())
        return cr->GetListOfMethods()->GetSize();
    else if (strcmp(cr.GetClassName(), "") == 0) {
        if (g_globalfuncs.empty()) {
            TCollection* funcs = gROOT->GetListOfGlobalFunctions(kTRUE);
	    g_globalfuncs.reserve(funcs->GetSize());

            TIter ifunc(funcs);

            TFunction* func = 0;
            while ((func = (TFunction*)ifunc.Next())) {
                if (strcmp(func->GetName(), "G__ateval") != 0)
                    g_globalfuncs.push_back(*func);
            }
        }
	return (int)g_globalfuncs.size();
    }
    return 0;
}

cppyy_index_t cppyy_method_index_at(cppyy_scope_t handle, int imeth) {
    TClassRef& cr = type_from_handle(handle);
    if (cr.GetClass())
        return (cppyy_index_t)imeth;
    return (cppyy_index_t)&g_globalfuncs[imeth];
}

cppyy_index_t* cppyy_method_indices_from_name(cppyy_scope_t handle, const char* name) {
    std::vector<cppyy_index_t> result;
    TClassRef& cr = type_from_handle(handle);
    if (cr.GetClass()) {
        gInterpreter->UpdateListOfMethods(cr.GetClass());
        int imeth = 0;
        TFunction* func;
        TIter next(cr->GetListOfMethods());
        while ((func = (TFunction*)next())) {
            if (strcmp(name, func->GetName()) == 0) {
                if (func->Property() & G__BIT_ISPUBLIC)
                    result.push_back((cppyy_index_t)imeth);
            }
            ++imeth;
        }
    }

    if (result.empty()) {
        TCollection* funcs = gROOT->GetListOfGlobalFunctions(kTRUE);
        TFunction* func = 0;
        TIter ifunc(funcs);
        while ((func = (TFunction*)ifunc.Next())) {
            if (strcmp(func->GetName(), name) == 0) {
                g_globalfuncs.push_back(*func);
                result.push_back((cppyy_index_t)func); 
            }
        }
    }

    if (result.empty())
        return (cppyy_index_t*)0;

    cppyy_index_t* llresult = (cppyy_index_t*)malloc(sizeof(cppyy_index_t)*result.size()+1);
    for (int i = 0; i < (int)result.size(); ++i) llresult[i] = result[i];
    llresult[result.size()] = -1;
    return llresult;
}


char* cppyy_method_name(cppyy_scope_t handle, cppyy_index_t idx) {
    TFunction* f = type_get_method(handle, idx);
    std::string name = f->GetName();
    TClassRef& cr = type_from_handle(handle);
    if (cr.GetClass() && cppyy_is_constructor(handle, idx))
        return cppstring_to_cstring(name);
    if (cppyy_method_is_template(handle, idx))
       return cppstring_to_cstring(name.substr(0, name.find('<')));
    return cppstring_to_cstring(name);
}

char* cppyy_method_result_type(cppyy_scope_t handle, cppyy_index_t idx) {
    TClassRef& cr = type_from_handle(handle);
    if (cr.GetClass() && cppyy_is_constructor(handle, idx))
        return cppstring_to_cstring("constructor");
    TFunction* f = type_get_method(handle, idx);
    return type_cppstring_to_cstring(f->GetReturnTypeName());
}

int cppyy_method_num_args(cppyy_scope_t handle, cppyy_index_t idx) {
    TFunction* f = type_get_method(handle, idx);
    return f->GetNargs();
}

int cppyy_method_req_args(cppyy_scope_t handle, cppyy_index_t idx) {
    TFunction* f = type_get_method(handle, idx);
    return f->GetNargs() - f->GetNargsOpt();
}

char* cppyy_method_arg_type(cppyy_scope_t handle, cppyy_index_t idx, int arg_index) {
    TFunction* f = type_get_method(handle, idx);
    TMethodArg* arg = (TMethodArg*)f->GetListOfMethodArgs()->At(arg_index);
    return type_cppstring_to_cstring(arg->GetFullTypeName());
}

char* cppyy_method_arg_default(cppyy_scope_t /*handle*/, cppyy_index_t /*idx*/, int /*arg_index*/) {
    /* unused: libffi does not work with CINT back-end */
    return cppstring_to_cstring("");
}

char* cppyy_method_signature(cppyy_scope_t handle, cppyy_index_t idx) {
    TClassRef& cr = type_from_handle(handle);
    TFunction* f = type_get_method(handle, idx);
    std::ostringstream sig;
    if (cr.GetClass() && cr->GetClassInfo()
        && strcmp(f->GetName(), ((G__ClassInfo*)cr->GetClassInfo())->Name()) != 0)
        sig << f->GetReturnTypeName() << " ";
    sig << cr.GetClassName() << "::" << f->GetName() << "(";
    int nArgs = f->GetNargs();
    for (int iarg = 0; iarg < nArgs; ++iarg) {
        sig << ((TMethodArg*)f->GetListOfMethodArgs()->At(iarg))->GetFullTypeName();
        if (iarg != nArgs-1)
            sig << ", ";
    }
    sig << ")" << std::ends;
    return cppstring_to_cstring(sig.str());
}


int cppyy_method_is_template(cppyy_scope_t handle, cppyy_index_t idx) {
    TClassRef& cr = type_from_handle(handle);
    TFunction* f = type_get_method(handle, idx);
    std::string name = f->GetName();
    return (name[name.size()-1] == '>') && (name.find('<') != std::string::npos);
}

int cppyy_method_num_template_args(cppyy_scope_t /*handle*/, cppyy_index_t /*idx*/) {
// TODO: somehow count from the actual arguments
    return 1;
}

char* cppyy_method_template_arg_name(
        cppyy_scope_t handle, cppyy_index_t idx, cppyy_index_t /*iarg*/) {
// TODO: return only the name for the requested arg
    TClassRef& cr = type_from_handle(handle);
    TFunction* f = type_get_method(handle, idx);
    std::string name = f->GetName();
    std::string::size_type pos = name.find('<');
    return cppstring_to_cstring(resolve_typedef(name.substr(pos+1, name.size()-pos-2)));
}


cppyy_method_t cppyy_get_method(cppyy_scope_t handle, cppyy_index_t idx) {
    TClassRef& cr = type_from_handle(handle);
    TFunction* f = type_get_method(handle, idx);
    if (cr && cr.GetClass() && !cr->IsLoaded()) {
        G__ClassInfo* gcl = (G__ClassInfo*)cr->GetClassInfo();
        if (gcl) {
            long offset;
            std::ostringstream sig;
            int nArgs = f->GetNargs();
            for (int iarg = 0; iarg < nArgs; ++iarg) {
                sig << ((TMethodArg*)f->GetListOfMethodArgs()->At(iarg))->GetFullTypeName();
                if (iarg != nArgs-1) sig << ", ";
            }
            G__MethodInfo gmi = gcl->GetMethod(
                f->GetName(), sig.str().c_str(), &offset, G__ClassInfo::ExactMatch);
            cppyy_method_t method = (cppyy_method_t)g_interpreted.size();
            g_interpreted.push_back(gmi);
            return method;
        }
    }
    cppyy_method_t method = (cppyy_method_t)f->InterfaceMethod();
    return method;
}

cppyy_index_t cppyy_get_global_operator(cppyy_scope_t scope, cppyy_scope_t lc, cppyy_scope_t rc, const char* op) {
    TClassRef& lccr = type_from_handle(lc);
    TClassRef& rccr = type_from_handle(rc);

    if (!lccr.GetClass() || !rccr.GetClass() || scope != GLOBAL_HANDLE)
        return (cppyy_index_t)-1;  // (void*)-1 is in kernel space, so invalid as a method handle

    std::string lcname = lccr->GetName();
    std::string rcname = rccr->GetName();

    std::string opname = "operator";
    opname += op;

    for (int idx = 0; idx < (int)g_globalfuncs.size(); ++idx) {
        TFunction* func = &g_globalfuncs[idx];
        if (func->GetListOfMethodArgs()->GetSize() != 2)
            continue;

        if (func->GetName() == opname) {
            if (lcname == resolve_typedef(((TMethodArg*)func->GetListOfMethodArgs()->At(0))->GetTypeName()) &&
                rcname == resolve_typedef(((TMethodArg*)func->GetListOfMethodArgs()->At(1))->GetTypeName())) {
                return (cppyy_index_t)func;
            }
        }
    }

    return (cppyy_index_t)-1;
}


/* method properties -----------------------------------------------------  */
int cppyy_is_constructor(cppyy_type_t handle, cppyy_index_t idx) {
    TClassRef& cr = type_from_handle(handle);
    TMethod* m = (TMethod*)cr->GetListOfMethods()->At(idx);
    return strcmp(m->GetName(), ((G__ClassInfo*)cr->GetClassInfo())->Name()) == 0;
}

int cppyy_is_staticmethod(cppyy_type_t handle, cppyy_index_t idx) {
    TClassRef& cr = type_from_handle(handle);
    TMethod* m = (TMethod*)cr->GetListOfMethods()->At(idx);
    return m->Property() & G__BIT_ISSTATIC;
}


/* data member reflection information ------------------------------------- */
int cppyy_num_datamembers(cppyy_scope_t handle) {
    TClassRef& cr = type_from_handle(handle);
    if (cr.GetClass() && cr->GetListOfDataMembers())
        return cr->GetListOfDataMembers()->GetSize();
    else if (strcmp(cr.GetClassName(), "") == 0) {
        TCollection* vars = gROOT->GetListOfGlobals(kTRUE);
       	if (g_globalvars.size() != (GlobalVars_t::size_type)vars->GetSize()) {
            g_globalvars.clear();
	    g_globalvars.reserve(vars->GetSize());

            TIter ivar(vars);

            TGlobal* var = 0;
            while ((var = (TGlobal*)ivar.Next()))
                g_globalvars.push_back(*var);

        }
	return (int)g_globalvars.size();
    }
    return 0;
}

char* cppyy_datamember_name(cppyy_scope_t handle, int datamember_index) {
    TClassRef& cr = type_from_handle(handle);
    if (cr.GetClass()) {
        TDataMember* m = (TDataMember*)cr->GetListOfDataMembers()->At(datamember_index);
        return cppstring_to_cstring(m->GetName());
    }
    TGlobal& gbl = g_globalvars[datamember_index];
    return cppstring_to_cstring(gbl.GetName());
}

char* cppyy_datamember_type(cppyy_scope_t handle, int datamember_index) {
    TClassRef& cr = type_from_handle(handle);
    if (cr.GetClass())  {
        TDataMember* m = (TDataMember*)cr->GetListOfDataMembers()->At(datamember_index);
        std::string fullType = m->GetFullTypeName();
        if ((int)m->GetArrayDim() > 1 || (!m->IsBasic() && m->IsaPointer()))
            fullType.append("*");
        else if ((int)m->GetArrayDim() == 1) {
            std::ostringstream s;
            s << '[' << m->GetMaxIndex(0) << ']' << std::ends;
            fullType.append(s.str());
        }
        return cppstring_to_cstring(fullType);
    }
    TGlobal& gbl = g_globalvars[datamember_index];
    return cppstring_to_cstring(gbl.GetFullTypeName());
}

size_t cppyy_datamember_offset(cppyy_scope_t handle, int datamember_index) {
    TClassRef& cr = type_from_handle(handle);
    if (cr.GetClass()) {
        TDataMember* m = (TDataMember*)cr->GetListOfDataMembers()->At(datamember_index);
        return (size_t)m->GetOffsetCint();
    }
    TGlobal& gbl = g_globalvars[datamember_index];
    return (size_t)gbl.GetAddress();
}

int cppyy_datamember_index(cppyy_scope_t handle, const char* name) {
    TClassRef& cr = type_from_handle(handle);
    if (cr.GetClass()) {
        // called from updates; add a hard reset as the code itself caches in
        // Class (TODO: by-pass ROOT/meta)
        Cppyy_OpenedTClass* c = (Cppyy_OpenedTClass*)cr.GetClass();
        if (c->fData) {
            c->fData->Delete();
            delete c->fData; c->fData = 0;
            delete c->fAllPubData; c->fAllPubData = 0;
        }
        // the following appears dumb, but TClass::GetDataMember() does a linear
        // search itself, so there is no gain
        int idm = 0;
        TDataMember* dm;
        TIter next(cr->GetListOfDataMembers());
        while ((dm = (TDataMember*)next())) {
            if (strcmp(name, dm->GetName()) == 0) {
                if (dm->Property() & G__BIT_ISPUBLIC)
                    return idm;
                return -1;
            }
            ++idm;
        }
    }
    TGlobal* gbl = (TGlobal*)gROOT->GetListOfGlobals(kTRUE)->FindObject(name);
    if (!gbl)
        return -1;
    int idx = g_globalvars.size();
    g_globalvars.push_back(*gbl);
    return idx;
}


/* data member properties ------------------------------------------------  */
int cppyy_is_publicdata(cppyy_scope_t handle, int datamember_index) {
    TClassRef& cr = type_from_handle(handle);
    if (cr.GetClass()) {
        TDataMember* m = (TDataMember*)cr->GetListOfDataMembers()->At(datamember_index);
        return m->Property() & G__BIT_ISPUBLIC;
    }
    return 1;  // global data is always public
}

int cppyy_is_staticdata(cppyy_scope_t handle, int datamember_index) {
    TClassRef& cr = type_from_handle(handle);
    if (cr.GetClass()) {
        TDataMember* m = (TDataMember*)cr->GetListOfDataMembers()->At(datamember_index);
        return m->Property() & G__BIT_ISSTATIC;
    }
    return 1;  // global data is always static
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


void* cppyy_load_dictionary(const char* lib_name) {
    if (0 <= gSystem->Load(lib_name))
        return (void*)1;
    return (void*)0;
}


/* pythonization helpers -------------------------------------------------- */
static std::map<long, std::pair<long, int> > s_tagnum2fid;

static int TFNPyCallback(G__value* res, G__CONST char*, struct G__param* libp, int hash) {
    // This is a generic CINT-installable TFN (with N=1,2,3) callback (used to factor
    // out some common code), to allow TFN to call back into python.

    std::pair<long, int> fid_and_npar = s_tagnum2fid[G__value_get_tagnum(res)];

    // callback (defined in cint_capi.py)
    double d = cppyy_tfn_callback(fid_and_npar.first, fid_and_npar.second,
       (double*)G__int(libp->para[0]), fid_and_npar.second ? (double*)G__int(libp->para[1]) : NULL);

    // translate result (TODO: error checking)
    G__letdouble( res, 100, d );
    return ( 1 || hash || res || libp );
}

long cppyy_tfn_install(const char* funcname, int npar) {
    // make a new function placeholder known to CINT
    static Long_t s_fid = (Long_t)cppyy_tfn_install;
    ++s_fid;

    const char* signature = "D - - 0 - - D - - 0 - -";

    // create a return type (typically masked/wrapped by a TPyReturn) for the method
    G__linked_taginfo pti;
    pti.tagnum = -1;
    pti.tagtype = 'c';
    std::string tagname("::py_");                 // used as a buffer
    tagname += funcname;
    pti.tagname = tagname.c_str();
    int tagnum = G__get_linked_tagnum(&pti);      // creates entry for new names

    // for free functions, add to global scope and add lookup through tp2f 
    // setup a connection between the pointer and the name
    Long_t hash = 0, len = 0;
    G__hash(funcname, hash, len);
    G__lastifuncposition();
    G__memfunc_setup(funcname, hash, (G__InterfaceMethod)&TFNPyCallback,
                     tagnum, tagnum, tagnum, 0, 2, 0, 1, 0, signature,
                     (char*)0, (void*)s_fid, 0);
    G__resetifuncposition();

    // setup a name in the global namespace (does not result in calls, so the signature
    // does not matter; but it makes subsequent GetMethod() calls work)
    G__MethodInfo meth = G__ClassInfo().AddMethod(
        funcname, funcname, signature, 1, 0, (void*)&TFNPyCallback);

    // store mapping so that the callback can find it
    s_tagnum2fid[tagnum] = std::make_pair(s_fid, npar);

    // hard to check result ... assume ok
    return s_fid;
}

cppyy_object_t cppyy_ttree_Branch(void* vtree, const char* branchname, const char* classname,
        void* addobj, int bufsize, int splitlevel) {
    // this little song-and-dance is to by-pass the handwritten Branch methods
    TBranch* b = ((TTree*)vtree)->Bronch(branchname, classname, (void*)&addobj, bufsize, splitlevel);
    if (b) b->SetObject(addobj);
    return (cppyy_object_t)b;
}

long long cppyy_ttree_GetEntry(void* vtree, long long entry) {
    return (long long)((TTree*)vtree)->GetEntry((Long64_t)entry);
}

cppyy_object_t cppyy_charp2TString(const char* str) {
    return (cppyy_object_t)new TString(str);
}

cppyy_object_t cppyy_TString2TString(cppyy_object_t ptr) {
    return (cppyy_object_t)new TString(*(TString*)ptr);
}
