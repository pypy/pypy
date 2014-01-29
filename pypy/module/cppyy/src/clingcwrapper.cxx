#include "cppyy.h"
#include "clingcwrapper.h"

/*************************************************************************
 * Copyright (C) 1995-2014, the ROOT team.                               *
 * LICENSE: LGPLv2.1; see http://root.cern.ch/drupal/content/license     *
 * CONTRIBUTORS: see http://root.cern.ch/drupal/content/contributors     *
 *************************************************************************/

#include <stdint.h>

#include "clang/AST/ASTContext.h"
#include "clang/AST/Decl.h"
#include "clang/AST/DeclBase.h"
#include "clang/AST/DeclCXX.h"
#include "clang/AST/PrettyPrinter.h"
#include "clang/AST/Type.h"
#include "clang/Frontend/CompilerInstance.h"
#include "clang/Sema/Sema.h"

#include "cling/Interpreter/DynamicLibraryManager.h"
#include "cling/Interpreter/Interpreter.h"
#include "cling/Interpreter/LookupHelper.h"
#include "cling/Interpreter/StoredValueRef.h"
#include "cling/MetaProcessor/MetaProcessor.h"

#include "llvm/ADT/SmallVector.h"
#include "llvm/ExecutionEngine/GenericValue.h"
#include "llvm/Support/raw_ostream.h"

#include <iostream>
#include <map>
#include <string>
#include <sstream>
#include <vector>

#include <stdlib.h>
#include <string.h>
#include <unistd.h>

using namespace clang;


/* cling initialization --------------------------------------------------- */
namespace {

cling::Interpreter* gCppyy_Cling;
cling::MetaProcessor* gCppyy_MetaProcessor;

struct Cppyy_InitCling { // TODO: check whether ROOT/meta's TCling is linked in
    Cppyy_InitCling() {
        std::vector<std::string> cling_args_storage;
        cling_args_storage.push_back("cling4cppyy");

        // TODO: get this from env
        cling_args_storage.push_back("-I/home/wlavrijsen/rootdev/root/etc");

        std::vector<const char*> interp_args;
        for (std::vector<std::string>::const_iterator iarg = cling_args_storage.begin();
                iarg != cling_args_storage.end(); ++iarg)
           interp_args.push_back(iarg->c_str());

        // TODO: get this from env
        const char* llvm_resource_dir = "/home/wlavrijsen/rootdev/root/etc/cling";
        gCppyy_Cling = new cling::Interpreter(
            interp_args.size(), &(interp_args[0]), llvm_resource_dir);

        // fInterpreter->installLazyFunctionCreator(llvmLazyFunctionCreator);

        {
            // R__LOCKGUARD(gInterpreterMutex);
            gCppyy_Cling->AddIncludePath("/home/wlavrijsen/rootdev/root/etc/cling");
            gCppyy_Cling->AddIncludePath(".");
        }

        // don't check whether modules' files exist.
        gCppyy_Cling->getCI()->getPreprocessorOpts().DisablePCHValidation = true;

        // Use a stream that doesn't close its file descriptor.
        static llvm::raw_fd_ostream fMPOuts (STDOUT_FILENO, /* ShouldClose */ false);
        gCppyy_MetaProcessor = new cling::MetaProcessor(*gCppyy_Cling, fMPOuts);

        gCppyy_Cling->enableDynamicLookup();
    }
} _init;

typedef std::map<std::string, cppyy_scope_t> NamedHandles_t;
static NamedHandles_t s_named;

struct SimpleScope {
    std::vector<FunctionDecl*> m_methods;
    std::vector<Decl*> m_data;
};

typedef std::map<cppyy_scope_t, SimpleScope*> Scopes_t;
static Scopes_t s_scopes;

typedef std::map<cppyy_method_t, CPPYY_Cling_Wrapper_t> Wrappers_t;
static Wrappers_t s_wrappers;

} // unnamed namespace


/* local helpers --------------------------------------------------------- */
static inline void print_error(const std::string& where, const std::string& what) {
    std::cerr << where << ": " << what << std::endl;
}

static inline char* cppstring_to_cstring(const std::string& name) {
    char* name_char = (char*)malloc(name.size() + 1);
    strcpy(name_char, name.c_str());
    return name_char;
}

static inline SimpleScope* scope_from_handle(cppyy_type_t handle) {
    return s_scopes[(cppyy_scope_t)handle];
}

static inline std::string qualtype_to_string(const QualType& qt, const ASTContext& atx) {
    std::string result;

    PrintingPolicy policy(atx.getPrintingPolicy());
    policy.SuppressTagKeyword = true;        // no class or struct keyword
    policy.SuppressScope = true;             // force scope from a clang::ElaboratedType
    policy.AnonymousTagLocations = false;    // no file name + line number for anonymous types
        // The scope suppression is required for getting rid of the anonymous part of the name
        // of a class defined in an anonymous namespace.
    
    qt.getAsStringInternal(result, policy);
    return result;
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
    return 0;
}

char* cppyy_resolve_name(const char* cppitem_name) {
    std::cout << " RESOLVING: " << cppitem_name << std::endl;
    return cppstring_to_cstring(cppitem_name);
}

cppyy_scope_t cppyy_get_scope(const char* scope_name) {
    const cling::LookupHelper& lh = gCppyy_Cling->getLookupHelper();
    const Type* type = 0;
    const Decl* decl = lh.findScope(scope_name, &type, /* intantiateTemplate= */ true);
    if (!decl) {
        //std::string buf = TClassEdit::InsertStd(name);
        //decl = lh.findScope(buf, &type, /* intantiateTemplate= */ true);
    }
    if (!decl && type) {
        const TagType* tagtype = type->getAs<TagType>();
        if (tagtype) {
            decl = tagtype->getDecl();
        }
    }

    std::cout << "FOR: " << scope_name << " RECEIVED: " << type << " AND: " << decl << std::endl;
    if (decl) {
        DeclContext* dc = llvm::cast<DeclContext>(const_cast<Decl*>(decl));
        SimpleScope* s = new SimpleScope;
        for (DeclContext::decl_iterator idecl = dc->decls_begin(); *idecl; ++idecl) {
            if (FunctionDecl* m = llvm::dyn_cast_or_null<FunctionDecl>(*idecl))
                s->m_methods.push_back(m);
            else if (FieldDecl* d = llvm::dyn_cast_or_null<FieldDecl>(*idecl))
                s->m_data.push_back(d);
        }
        s_scopes[(cppyy_scope_t)decl] = s;
    }

    return (cppyy_scope_t)decl;    // lookup failure return 0 (== error)
}


/* method/function dispatching -------------------------------------------- */

// TODO: expect the below to live in libCling.so
static CPPYY_Cling_Wrapper_t make_wrapper(const FunctionDecl* fdecl);
static void exec_with_valref_return(void* address, cling::StoredValueRef* ret, const FunctionDecl*);
static long long sv_to_long_long(const cling::StoredValueRef& svref);
// -- TODO: expect the above to live in libCling.so


template<typename T>
static inline T cppyy_call_T(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    if (s_wrappers.find(method) == s_wrappers.end()) {
        make_wrapper((FunctionDecl*)method);
    }
    cling::StoredValueRef ret;
    //    std::vector<void*> arguments = build_args(nargs, args);
    //    CPPYY_Cling_Wrapper_t cb = (CPPYY_Cling_Wrapper_t)method;
    exec_with_valref_return((void*)self, &ret, (FunctionDecl*)method);
    //    (*cb)((void*)self, nargs, const_cast<void**>(arguments.data()), ret);
    return static_cast<T>(sv_to_long_long(ret));
}



int cppyy_call_i(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    return cppyy_call_T<int>(method, self, nargs, args);
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
    for (NamedHandles_t::iterator isp = s_named.begin(); isp != s_named.end(); ++isp) {
        if (isp->second == (cppyy_scope_t)handle)
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
    SimpleScope* s = scope_from_handle(handle);
    if (!s) return 0;
    return s->m_methods.size();
}

cppyy_index_t cppyy_method_index_at(cppyy_scope_t /* scope */, int imeth) {
    return (cppyy_index_t)imeth;
}

char* cppyy_method_name(cppyy_scope_t handle, cppyy_index_t method_index) {
    SimpleScope* s = scope_from_handle(handle);
    if (!s) return cppstring_to_cstring("<unknown>");
    FunctionDecl* meth = s->m_methods.at(method_index);
    std::cout << " METHOD NAME: " << meth->getDeclName().getAsString() << std::endl;
    return cppstring_to_cstring(meth->getDeclName().getAsString());
}

char* cppyy_method_result_type(cppyy_scope_t handle, cppyy_index_t method_index) {
    SimpleScope* s = scope_from_handle(handle);
    if (!s) return cppstring_to_cstring("<unknown>");
    FunctionDecl* meth = s->m_methods.at(method_index);
    const std::string& ret_type =
        qualtype_to_string(meth->getCallResultType(), meth->getASTContext());
    std::cout << "    -> RET TYPE: " << ret_type << std::endl;
    return cppstring_to_cstring(ret_type);
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
    
cppyy_method_t cppyy_get_method(cppyy_scope_t handle, cppyy_index_t method_index) {
    SimpleScope* s = scope_from_handle(handle);
    if (!s) return (cppyy_method_t)0;
    return (cppyy_method_t)s->m_methods.at(method_index);
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


void* cppyy_load_dictionary(const char* lib_name) {
    // TODO: need to rethink this; for now it creates reflection info from
    //       <lib_name>.h while loading lib<lib_name>.so

    // Load a library file in cling's memory.
    // if 'system' is true, the library is never unloaded.
    // Return 0 on success, -1 on failure.
    // R__LOCKGUARD2(gInterpreterMutex);
    std::cout << " NOW LOADING: " << lib_name << std::endl;

    cling::StoredValueRef call_res;
    cling::Interpreter::CompilationResult comp_res = cling::Interpreter::kSuccess;
    std::ostringstream line;
    line << "#include \"" << lib_name << ".h\"";
    gCppyy_MetaProcessor->process(line.str().c_str(), comp_res, &call_res);

    std::string to_load = "lib";
    to_load += lib_name;
    to_load += ".so";
    cling::DynamicLibraryManager::LoadLibResult res
        = gCppyy_Cling->getDynamicLibraryManager()->loadLibrary(to_load, /* not unload */ true);
    // if (res == cling::DynamicLibraryManager::kLoadLibSuccess) {
    //     UpdateListOfLoadedSharedLibraries();
    // }
    switch (res) {
    case cling::DynamicLibraryManager::kLoadLibSuccess: return (void*)1;
    case cling::DynamicLibraryManager::kLoadLibExists:  return (void*)2;
    default: break;
    };
    return (void*)1;
}


/* to-be libCling code taken from ROOT/meta ------------------------------- */

// TODO: expect the below to live in libCling.so

template <typename T>
T sv_to_long_long_u_or_not(const cling::StoredValueRef& svref) {
    const cling::Value& valref = svref.get();
    QualType QT = valref.getClangType();
    if (QT.isNull()) {
        print_error("sv_to_long_long_u_or_not", "null type!");
        return 0;
    }
    llvm::GenericValue gv = valref.getGV();
    if (QT->isMemberPointerType()) {
        const MemberPointerType* MPT =
            QT->getAs<MemberPointerType>();
        if (MPT->isMemberDataPointer()) {
            return (T) (ptrdiff_t) gv.PointerVal;
        }
        return (T) gv.PointerVal;
    }
    if (QT->isPointerType() || QT->isArrayType() || QT->isRecordType() ||
        QT->isReferenceType()) {
        return (T) gv.PointerVal;
    }
    if (const EnumType* ET = llvm::dyn_cast<EnumType>(&*QT)) {
        if (ET->getDecl()->getIntegerType()->hasSignedIntegerRepresentation())
            return (T) gv.IntVal.getSExtValue();
        else
            return (T) gv.IntVal.getZExtValue();
    }
    if (const BuiltinType* BT = llvm::dyn_cast<BuiltinType>(&*QT)) {
      if (BT->isSignedInteger()) {
          return gv.IntVal.getSExtValue();
      } else if (BT->isUnsignedInteger()) {
          return (T) gv.IntVal.getZExtValue();
      } else {
          switch (BT->getKind()) {
          case BuiltinType::Float:
              return (T) gv.FloatVal;
          case BuiltinType::Double:
              return (T) gv.DoubleVal;
          case BuiltinType::LongDouble:
              // FIXME: Implement this!
              break;
          case BuiltinType::NullPtr:
              // C++11 nullptr
              return 0;
          default: break;
          }
      }
    }
    print_error("sv_to_long_long_u_or_not", "cannot handle this type!");
    QT->dump();
    return 0;
}

static long long sv_to_long_long(const cling::StoredValueRef& svref) {
    return sv_to_long_long_u_or_not<long long>(svref);
}

static
unsigned long long sv_to_ulong_long(const cling::StoredValueRef& svref) {
   return sv_to_long_long_u_or_not<unsigned long long>(svref);
}


namespace {

class ValHolder {
public:
   union {
      long double ldbl;
      double dbl;
      float flt;
      //__uint128_t ui128;
      //__int128_t i128;
      unsigned long long ull;
      long long ll;
      unsigned long ul;
      long l;
      unsigned int ui;
      int i;
      unsigned short us;
      short s;
      //char32_t c32;
      //char16_t c16;
      //unsigned wchar_t uwc; - non-standard
      wchar_t wc;
      unsigned char uc;
      signed char sc;
      char c;
      bool b;
      void* vp;
   } u;
};

} // unnamed namespace

static void exec(void* address, void* ret, const FunctionDecl* fdecl) {
    std::vector<ValHolder> vh_ary;
    std::vector<void*> vp_ary;

    //
    //  Convert the arguments from cling::StoredValueRef to their
    //  actual type and store them in a holder for passing to the
    //  wrapper function by pointer to value.
    //
    unsigned num_params = fdecl->getNumParams();
    /*    unsigned num_args = fArgVals.size();

    if (num_args < fdecl->getMinRequiredArguments ()) {
        Error("TClingCallFunc::exec",
              "Not enough arguments provided for %s (%d instead of the minimum %d)",
              fMethod->Name(ROOT::TMetaUtils::TNormalizedCtxt(fInterp->getLookupHelper())),
              num_args,fdecl->getMinRequiredArguments ());
        return;
    }
    if (address == 0 && llvm::dyn_cast<CXXMethodDecl>(fdecl)
        && !(llvm::dyn_cast<CXXMethodDecl>(fdecl))->isStatic()
        && !llvm::dyn_cast<CXXConstructorDecl>(fdecl)) {
        Error("TClingCallFunc::exec",
              "The method %s is called without an object.",
              fMethod->Name(ROOT::TMetaUtils::TNormalizedCtxt(fInterp->getLookupHelper())));
        return;
    }
    vh_ary.reserve(num_args);
    vp_ary.reserve(num_args);
    for (unsigned i = 0U; i < num_args; ++i) {
        QualType Ty;
        if (i < num_params) {
            const ParmVarDecl* PVD = fdecl->getParamDecl(i);
            Ty = PVD->getType();
        }
        else {
            Ty = fArgVals[i].get().getClangType();
        }
        QualType QT = Ty.getCanonicalType();
        if (QT->isReferenceType()) {
            ValHolder vh;
            vh.u.vp = (void*) sv_to_ulong_long(fArgVals[i]);
            vh_ary.push_back(vh);
            vp_ary.push_back(&vh_ary.back());
        }
        else if (QT->isMemberPointerType()) {
            ValHolder vh;
            vh.u.vp = (void*) sv_to_ulong_long(fArgVals[i]);
            vh_ary.push_back(vh);
            vp_ary.push_back(&vh_ary.back());
        }
        else if (QT->isPointerType() || QT->isArrayType()) {
            ValHolder vh;
            vh.u.vp = (void*) sv_to_ulong_long(fArgVals[i]);
            vh_ary.push_back(vh);
            vp_ary.push_back(&vh_ary.back());
        }
        else if (QT->isRecordType()) {
            ValHolder vh;
            vh.u.vp = (void*) sv_to_ulong_long(fArgVals[i]);
            vh_ary.push_back(vh);
            vp_ary.push_back(&vh_ary.back());
        }
        else if (const EnumType* ET = llvm::dyn_cast<EnumType>(&*QT)) {
            // Note: We may need to worry about the underlying type
            //       of the enum here.
            (void) ET;
            ValHolder vh;
            vh.u.i = (int) sv_to_long_long(fArgVals[i]);
            vh_ary.push_back(vh);
            vp_ary.push_back(&vh_ary.back());
        }
        else if (const BuiltinType* BT = llvm::dyn_cast<BuiltinType>(&*QT)) {
            //
            //  WARNING!!!
            //
            //  This switch is organized in order-of-declaration
            //  so that the produced assembly code is optimal.
            //  Do not reorder!
            //
            switch (BT->getKind()) {
            //
            //  Builtin Types
            //
            case BuiltinType::Void: {
                // void
                print_error("exec", "invalid argument type (void)");
                return;
            }
            //
            //  Unsigned Types
            //
            case BuiltinType::Bool: {
                // bool
                ValHolder vh;
                vh.u.b = (bool) sv_to_ulong_long(fArgVals[i]);
                vh_ary.push_back(vh);
                vp_ary.push_back(&vh_ary.back());
                break;
            }
            case BuiltinType::Char_U: {
                // char on targets where it is unsigned
                ValHolder vh;
                vh.u.c = (char) sv_to_ulong_long(fArgVals[i]);
                vh_ary.push_back(vh);
                vp_ary.push_back(&vh_ary.back());
                break;
            }
            case BuiltinType::UChar: {
                // unsigned char
                ValHolder vh;
                vh.u.uc = (unsigned char) sv_to_ulong_long(fArgVals[i]);
                vh_ary.push_back(vh);
                vp_ary.push_back(&vh_ary.back());
                break; 
            }
            case BuiltinType::WChar_U: {
                // wchar_t on targets where it is unsigned.
                // The standard doesn't allow to specify signednedd of wchar_t
                // thus this maps simply to wchar_t.
                ValHolder vh;
                vh.u.wc = (wchar_t) sv_to_ulong_long(fArgVals[i]);
                vh_ary.push_back(vh);
                vp_ary.push_back(&vh_ary.back());
                break;
            }
            case BuiltinType::Char16:
            case BuiltinType::Char32: {
                print_error("exec", "unsupported argument");
                QT->dump();
                return;
            }
            case BuiltinType::UShort: {
                // unsigned short
                ValHolder vh;
                vh.u.us = (unsigned short) sv_to_ulong_long(fArgVals[i]);
                vh_ary.push_back(vh);
                vp_ary.push_back(&vh_ary.back());
                break;
            }
            case BuiltinType::UInt: {
                // unsigned int
                ValHolder vh;
                vh.u.ui = (unsigned int) sv_to_ulong_long(fArgVals[i]);
                vh_ary.push_back(vh);
                vp_ary.push_back(&vh_ary.back());
                break;
            }
            case BuiltinType::ULong: {
                // unsigned long
                ValHolder vh;
                vh.u.ul = (unsigned long) sv_to_ulong_long(fArgVals[i]);
                vh_ary.push_back(vh);
                vp_ary.push_back(&vh_ary.back());
                break;
            }
            case BuiltinType::ULongLong: {
                // unsigned long long
                ValHolder vh;
                vh.u.ull = (unsigned long long) sv_to_ulong_long(fArgVals[i]);
                vh_ary.push_back(vh);
                vp_ary.push_back(&vh_ary.back());
                break;
            }
            case BuiltinType::UInt128: {
                print_error("exec", "unsupported argument");
                QT->dump();
                return;
            }
            //
            //  Signed Types
            //
            case BuiltinType::Char_S: {
                // char on targets where it is signed
                ValHolder vh;
                vh.u.c = (char) sv_to_long_long(fArgVals[i]);
                vh_ary.push_back(vh);
                vp_ary.push_back(&vh_ary.back());
                break;
            }
            case BuiltinType::SChar: {
                // signed char
                ValHolder vh;
                vh.u.sc = (signed char) sv_to_long_long(fArgVals[i]);
                vh_ary.push_back(vh);
                vp_ary.push_back(&vh_ary.back());
                break;
            }
            case BuiltinType::WChar_S: {
                // wchar_t on targets where it is signed.
                // The standard doesn't allow to specify signednedd of wchar_t
                // thus this maps simply to wchar_t.
                ValHolder vh;
                vh.u.wc = (wchar_t) sv_to_long_long(fArgVals[i]);
                vh_ary.push_back(vh);
                vp_ary.push_back(&vh_ary.back());
                break;
            }
            case BuiltinType::Short: {
                // short
                ValHolder vh;
                vh.u.s = (short) sv_to_long_long(fArgVals[i]);
                vh_ary.push_back(vh);
                vp_ary.push_back(&vh_ary.back());
                break;
            }
            case BuiltinType::Int: {
                // int
                ValHolder vh;
                vh.u.i = (int) sv_to_long_long(fArgVals[i]);
                vh_ary.push_back(vh);
                vp_ary.push_back(&vh_ary.back());
                break;
            }
            case BuiltinType::Long: {
                // long
                ValHolder vh;
                vh.u.l = (long) sv_to_long_long(fArgVals[i]);
                vh_ary.push_back(vh);
                vp_ary.push_back(&vh_ary.back());
                break;
            }
            case BuiltinType::LongLong: {
                // long long
                ValHolder vh;
                vh.u.ll = (long long) sv_to_long_long(fArgVals[i]);
                vh_ary.push_back(vh);
                vp_ary.push_back(&vh_ary.back());
                break;
            }
            case BuiltinType::Int128:
            case BuiltinType::Half: {
                // half in OpenCL, __fp16 in ARM NEON
                print_error("exec", "unsupported argument");
                QT->dump();
                return;
            }
            case BuiltinType::Float: {
                // float
                ValHolder vh;
                vh.u.flt = sv_to<float>(fArgVals[i]);
                vh_ary.push_back(vh);
                vp_ary.push_back(&vh_ary.back());
                break;
            }
            case BuiltinType::Double: {
                // double
                ValHolder vh;
                vh.u.dbl = sv_to<double>(fArgVals[i]);
                vh_ary.push_back(vh);
                vp_ary.push_back(&vh_ary.back());
                break;
            }
            case BuiltinType::LongDouble: {
                // long double
                print_error("exec", "unsupported argument");
                QT->dump();
                return;
            }
            //
            //  Language-Specific Types
            //
            case BuiltinType::NullPtr: {
                // C++11 nullptr
                ValHolder vh;
                vh.u.vp = (void*) fArgVals[i].get().getGV().PointerVal;
                vh_ary.push_back(vh);
                vp_ary.push_back(&vh_ary.back());
                break;
            }
            default: {
                print_error("exec", "unsupported argument");
                QT->dump();
                return;
            }
         }
      }
      else {
          print_error("exec", "invalid type (unrecognized)!");
          QT->dump();
          return;
      }
      }*/

    CPPYY_Cling_Wrapper_t wrapper = s_wrappers[(cppyy_method_t)fdecl];
    (*wrapper)(address, (int)0/*num_args*/, (void**)vp_ary.data(), ret);
}


static void exec_with_valref_return(void* address, cling::StoredValueRef* ret, const FunctionDecl* fdecl) {
    if (!ret) {
        exec(address, 0, fdecl);
        return;
    }
    std::cout << " USING DECL: " << fdecl << std::endl;
    fdecl->dump();
    ASTContext& Context = fdecl->getASTContext();

    if (const CXXConstructorDecl* CD = llvm::dyn_cast<CXXConstructorDecl>(fdecl)) {
        const TypeDecl* TD = llvm::dyn_cast<TypeDecl>(CD->getDeclContext());
        QualType ClassTy(TD->getTypeForDecl(), 0);
        QualType QT = Context.getLValueReferenceType(ClassTy);
        llvm::GenericValue gv;
        exec(address, &gv.PointerVal, fdecl);
        *ret = cling::StoredValueRef::bitwiseCopy(
            *gCppyy_Cling, cling::Value(gv, QT));
        return;
    }
    QualType QT = fdecl->getResultType().getCanonicalType();
    if (QT->isReferenceType()) {
        llvm::GenericValue gv;
        exec(address, &gv.PointerVal, fdecl);
        *ret = cling::StoredValueRef::bitwiseCopy(
            *gCppyy_Cling, cling::Value(gv, QT));
        return;
    }
    else if (QT->isMemberPointerType()) {
        const MemberPointerType* MPT =
            QT->getAs<MemberPointerType>();
        if (MPT->isMemberDataPointer()) {
            // A member data pointer is a actually a struct with one
            // member of ptrdiff_t, the offset from the base of the object
            // storage to the storage for the designated data member.
            llvm::GenericValue gv;
            exec(address, &gv.PointerVal, fdecl);
            *ret = cling::StoredValueRef::bitwiseCopy(
                *gCppyy_Cling, cling::Value(gv, QT));
            return;
        }
        // We are a function member pointer.
        llvm::GenericValue gv;
        exec(address, &gv.PointerVal, fdecl);
        *ret = cling::StoredValueRef::bitwiseCopy(
            *gCppyy_Cling, cling::Value(gv, QT));
        return;
    }
    else if (QT->isPointerType() || QT->isArrayType()) {
        // Note: ArrayType is an illegal function return value type.
        llvm::GenericValue gv;
        exec(address, &gv.PointerVal, fdecl);
        *ret = cling::StoredValueRef::bitwiseCopy(
            *gCppyy_Cling, cling::Value(gv, QT));
        return;
    }
    else if (QT->isRecordType()) {
        uint64_t size = Context.getTypeSizeInChars(QT).getQuantity();
        void* p = ::operator new(size);
        exec(address, p, fdecl);
        *ret = cling::StoredValueRef::bitwiseCopy(
            *gCppyy_Cling, cling::Value(llvm::PTOGV(p), QT));
        return;
    }
    else if (const EnumType* ET = llvm::dyn_cast<EnumType>(&*QT)) {
        // Note: We may need to worry about the underlying type
        //       of the enum here.
        (void) ET;
        uint64_t numBits = Context.getTypeSize(QT);
        int retVal = 0;
        exec(address, &retVal, fdecl);
        llvm::GenericValue gv;
        gv.IntVal = llvm::APInt(numBits, (uint64_t)retVal, true /*isSigned*/);
        *ret =  cling::StoredValueRef::bitwiseCopy(
            *gCppyy_Cling, cling::Value(gv, QT));
        return;
    }
    else if (const BuiltinType* BT = llvm::dyn_cast<BuiltinType>(&*QT)) {
        llvm::GenericValue gv;

        uint64_t numBits = Context.getTypeSize(QT);
        switch (BT->getKind()) {
        //
        //  builtin types
        //
        case BuiltinType::Void: {
            exec(address, 0, fdecl);
            return;
        }
        //
        //  unsigned integral types
        //
        case BuiltinType::Bool: {
            bool retVal = false;
            exec(address, &retVal, fdecl);
            gv.IntVal = llvm::APInt(numBits, (uint64_t)retVal, false /*isSigned*/);
            break;
        }
        case BuiltinType::Char_U: {
            // char on targets where it is unsigned
            char retVal = '\0';
            exec(address, &retVal, fdecl);
            gv.IntVal = llvm::APInt(numBits, (uint64_t) retVal, false /*isSigned*/);
            break;
        }
        case BuiltinType::UChar: {
            unsigned char retVal = '\0';
            exec(address, &retVal, fdecl);
            gv.IntVal = llvm::APInt(numBits, (uint64_t) retVal, false /*isSigned*/);
            break;
        }
        case BuiltinType::WChar_U: {
            // wchar_t on targets where it is unsigned.
            // The standard doesn't allow to specify signedness of wchar_t
            // thus this maps simply to wchar_t.
            wchar_t retVal = L'\0';
            exec(address, &retVal, fdecl);
            gv.IntVal = llvm::APInt(numBits, (uint64_t) retVal, false /*isSigned*/);
            break;
        }
        case BuiltinType::UShort: {
            unsigned short retVal = 0;
            exec(address, &retVal, fdecl);
            gv.IntVal = llvm::APInt(numBits, (uint64_t) retVal, false /*isSigned*/);
            break;
        }
        case BuiltinType::UInt: {
            unsigned int retVal = 0;
            exec(address, &retVal, fdecl);
            gv.IntVal = llvm::APInt(numBits, (uint64_t) retVal, false /*isSigned*/);
            break;
        }
        case BuiltinType::ULong: {
            // unsigned long
            unsigned long retVal = 0;
            exec(address, &retVal, fdecl);
            gv.IntVal = llvm::APInt(numBits, (uint64_t) retVal, false /*isSigned*/);
            break;
        }
        case BuiltinType::ULongLong: {
            // unsigned long long
            unsigned long long retVal = 0;
            exec(address, &retVal, fdecl);
            gv.IntVal = llvm::APInt(numBits, (uint64_t) retVal, false /*isSigned*/);
            break;
        }
        //
        //  signed integral types
        //
        case BuiltinType::Char_S: {
            // char on targets where it is signed
            char retVal = '\0';
            exec(address, &retVal, fdecl);
            gv.IntVal = llvm::APInt(numBits, (uint64_t) retVal, true /*isSigned*/);
            break;
        }
        case BuiltinType::SChar: {
            // signed char
            signed char retVal = '\0';
            exec(address, &retVal, fdecl);
            gv.IntVal = llvm::APInt(numBits, (uint64_t) retVal, true /*isSigned*/);
            break;
        }
        case BuiltinType::WChar_S: {
            // wchar_t on targets where it is signed.
            // The standard doesn't allow to specify signednedd of wchar_t
            // thus this maps simply to wchar_t.
            wchar_t retVal = L'\0';
            exec(address, &retVal, fdecl);
            gv.IntVal = llvm::APInt(numBits, (uint64_t) retVal, true /*isSigned*/);
            break;
        }
        case BuiltinType::Short: {
            // short
            short retVal = 0;
            exec(address, &retVal, fdecl);
            gv.IntVal = llvm::APInt(numBits, (uint64_t) retVal, true /*isSigned*/);
            break;
        }
        case BuiltinType::Int: {
            // int
            int retVal = 0;
            exec(address, &retVal, fdecl);
            gv.IntVal = llvm::APInt(numBits, (uint64_t) retVal, true /*isSigned*/);
            break;
        }
        case BuiltinType::Long: {
            long retVal = 0;
            exec(address, &retVal, fdecl);
            gv.IntVal = llvm::APInt(numBits, (uint64_t) retVal, true /*isSigned*/);
            break;
        }
        case BuiltinType::LongLong: {
            long long retVal = 0;
            exec(address, &retVal, fdecl);
            gv.IntVal = llvm::APInt(numBits, (uint64_t) retVal, true /*isSigned*/);
            break;
        }
        case BuiltinType::Float: {
            exec(address, &gv.FloatVal, fdecl);
            break;
        }
        case BuiltinType::Double: {
            exec(address, &gv.DoubleVal, fdecl);
            break;
        }
        case BuiltinType::Char16:
        case BuiltinType::Char32:
        case BuiltinType::Half:
        case BuiltinType::Int128:
        case BuiltinType::UInt128:
        case BuiltinType::LongDouble: 
        case BuiltinType::NullPtr:
        default: {
            print_error("exec_with_valref", "unsupported return type");
            return;
        }
        }

        *ret = cling::StoredValueRef::bitwiseCopy(*gCppyy_Cling, cling::Value(gv, QT));
        return;
    }

    std::cout << "exec_with_valref: some error occurred ... " << std::endl;
}


static const std::string indent_string("   ");
static unsigned long long wrapper_serial = 0LL;

void collect_type_info(QualType& QT, std::ostringstream& typedefbuf,
        std::ostringstream& callbuf, std::string& type_name, bool& isReference,
        int& ptrCnt, int indent_level, bool forArgument, const FunctionDecl* fdecl) {
    //
    //  Collect information about type type of a function parameter
    //  needed for building the wrapper function.
    //
    PrintingPolicy Policy(fdecl->getASTContext().getPrintingPolicy());
    isReference = false;
    ptrCnt = 0;
    if (QT->isRecordType() && forArgument) {
        // Note: We treat object of class type as if it were a reference
        //       type because we hold it by pointer.
        isReference = true;
        QT.getAsStringInternal(type_name, Policy);
        // And drop the default arguments if any (at least until the clang
        // type printer properly handle template paratemeter that are enumerator).
        //R__DropDefaultArg(type_name);
        return;
    }
    while (1) {
        if (QT->isArrayType()) {
            ++ptrCnt;
            QT = cast<clang::ArrayType>(QT)->getElementType();
            continue;
        }
        else if (QT->isFunctionPointerType()) {
            std::string fp_typedef_name;
            {
                std::ostringstream nm;
                nm << "FP" << wrapper_serial++;
                type_name = nm.str();
                llvm::raw_string_ostream OS(fp_typedef_name);
                QT.print(OS, Policy, type_name);
                OS.flush();
            }
            for (int i = 0; i < indent_level; ++i) {
                typedefbuf << indent_string;
            }
            typedefbuf << "typedef " << fp_typedef_name << ";\n";
            break;
        }
        else if (QT->isMemberPointerType()) {
            std::string mp_typedef_name;
            {
                std::ostringstream nm;
                nm << "MP" << wrapper_serial++;
                type_name = nm.str();
                llvm::raw_string_ostream OS(mp_typedef_name);
                QT.print(OS, Policy, type_name);
                OS.flush();
            }
            for (int i = 0; i < indent_level; ++i) {
                typedefbuf << indent_string;
            }
            typedefbuf << "typedef " << mp_typedef_name << ";\n";
            break;
        }
        else if (QT->isPointerType()) {
            ++ptrCnt;
            QT = cast<clang::PointerType>(QT)->getPointeeType();
            continue;
        }
        else if (QT->isReferenceType()) {
            isReference = true;
            QT = cast<ReferenceType>(QT)->getPointeeType();
            continue;
        }
        QT.getAsStringInternal(type_name, Policy);
        break;
    }
    // And drop the default arguments if any (at least until the clang
    // type printer properly handle template paratemeter that are enumerator).
    // R__DropDefaultArg(type_name);
}

void make_narg_ctor(const unsigned N, std::ostringstream& typedefbuf,
         std::ostringstream& callbuf, const std::string& class_name,
         int indent_level, const FunctionDecl* fdecl) {
    // Make a code string that follows this pattern:
    //
    // new ClassName(args...)
    //
    callbuf << "new " << class_name << "(";
    for (unsigned i = 0U; i < N; ++i) {
        const ParmVarDecl* PVD = fdecl->getParamDecl(i);
        QualType Ty = PVD->getType();
        QualType QT = Ty.getCanonicalType();
        std::string type_name;
        bool isReference = false;
        int ptrCnt = 0;
        collect_type_info(QT, typedefbuf, callbuf, type_name,
                          isReference, ptrCnt, indent_level, true, fdecl);
        if (i) {
            callbuf << ',';
            if (i % 2) {
                callbuf << ' ';
            }
            else {
                callbuf << "\n";
                for (int j = 0; j <= indent_level; ++j) {
                    callbuf << indent_string;
                }
            }
        }
        if (isReference) {
            std::string stars;
            for (int j = 0; j < ptrCnt; ++j) {
                stars.push_back('*');
            }
            callbuf << "**(" << type_name.c_str() << stars << "**)args["
                    << i << "]";
        }
        else if (ptrCnt) {
            std::string stars;
            for (int j = 0; j < ptrCnt; ++j) {
                stars.push_back('*');
            }
            callbuf << "*(" << type_name.c_str() << stars << "*)args["
                    << i << "]";
        }
        else {
            callbuf << "*(" << type_name.c_str() << "*)args[" << i << "]";
        }
    }
    callbuf << ")";
}

void make_narg_call(const unsigned N, std::ostringstream& typedefbuf,
        std::ostringstream& callbuf, const std::string& class_name,int indent_level, const FunctionDecl* fdecl) {
    //
    // Make a code string that follows this pattern:
    //
    // ((<class>*)obj)-><method>(*(<arg-i-type>*)args[i], ...)
    //
    if (const CXXMethodDecl* MD = llvm::dyn_cast<CXXMethodDecl>(fdecl)) {
        // This is a class, struct, or union member.
        if (MD->isConst())
            callbuf << "((const " << class_name << "*)obj)->";
        else
            callbuf << "((" << class_name << "*)obj)->";
    }
    else if (const NamedDecl* ND = llvm::dyn_cast<NamedDecl>(fdecl->getDeclContext())) {
        // This is a namespace member.
        (void) ND;
        callbuf << class_name << "::";
    }
    //   callbuf << fMethod->Name() << "(";
    {
        std::string name;
        {
            llvm::raw_string_ostream stream(name);
            fdecl->getNameForDiagnostic(stream, fdecl->getASTContext().getPrintingPolicy(), /*Qualified=*/false);
        }
        callbuf << name << "(";
    }
    for (unsigned i = 0U; i < N; ++i) {
        const ParmVarDecl* PVD = fdecl->getParamDecl(i);
        QualType Ty = PVD->getType();
        QualType QT = Ty.getCanonicalType();
        std::string type_name;
        bool isReference = false;
        int ptrCnt = 0;
        collect_type_info(QT, typedefbuf, callbuf, type_name,
                          isReference, ptrCnt, indent_level, true, fdecl);
        if (i) {
            callbuf << ',';
            if (i % 2) {
                callbuf << ' ';
            }
            else {
                callbuf << "\n";
                for (int j = 0; j <= indent_level; ++j) {
                    callbuf << indent_string;
                }
            }
        }
        if (isReference) {
            std::string stars;
            for (int j = 0; j < ptrCnt; ++j) {
                stars.push_back('*');
            }
            callbuf << "**(" << type_name.c_str() << stars << "**)args["
                    << i << "]";
        }
        else if (ptrCnt) {
            std::string stars;
            for (int j = 0; j < ptrCnt; ++j) {
                stars.push_back('*');
            }
            callbuf << "*(" << type_name.c_str() << stars << "*)args["
                    << i << "]";
        }
        else {
            callbuf << "*(" << type_name.c_str() << "*)args[" << i << "]";
        }
    }
    callbuf << ")";
}

void make_narg_ctor_with_return(const unsigned N, const std::string& class_name,
        std::ostringstream& buf, int indent_level, const FunctionDecl* fdecl) {
    // Make a code string that follows this pattern:
    //
    // if (ret) {
    //    (*(ClassName**)ret) = new ClassName(args...);
    // }
    // else {
    //    new ClassName(args...);
    // }
    //
    for (int i = 0; i < indent_level; ++i) {
        buf << indent_string;
    }
    buf << "if (ret) {\n";
    ++indent_level;
    {
        std::ostringstream typedefbuf;
        std::ostringstream callbuf;
        //
        //  Write the return value assignment part.
        //
        for (int i = 0; i < indent_level; ++i) {
            callbuf << indent_string;
        }
        callbuf << "(*(" << class_name << "**)ret) = ";
        //
        //  Write the actual new expression.
        //
        make_narg_ctor(N, typedefbuf, callbuf, class_name, indent_level, fdecl);
        //
        //  End the new expression statement.
        //
        callbuf << ";\n";
        for (int i = 0; i < indent_level; ++i) {
            callbuf << indent_string;
        }
        callbuf << "return;\n";
        //
        //  Output the whole new expression and return statement.
        //
        buf << typedefbuf.str() << callbuf.str();
    }
    --indent_level;
    for (int i = 0; i < indent_level; ++i) {
        buf << indent_string;
    }
    buf << "}\n";
   for (int i = 0; i < indent_level; ++i) {
      buf << indent_string;
   }
   buf << "else {\n";
   ++indent_level;
   {
       std::ostringstream typedefbuf;
       std::ostringstream callbuf;
       for (int i = 0; i < indent_level; ++i) {
           callbuf << indent_string;
       }
       make_narg_ctor(N, typedefbuf, callbuf, class_name, indent_level, fdecl);
       callbuf << ";\n";
       for (int i = 0; i < indent_level; ++i) {
           callbuf << indent_string;
       }
       callbuf << "return;\n";
       buf << typedefbuf.str() << callbuf.str();
   }
   --indent_level;
   for (int i = 0; i < indent_level; ++i) {
       buf << indent_string;
   }
   buf << "}\n";
}

void make_narg_call_with_return(const unsigned N, const std::string& class_name,
        std::ostringstream& buf, int indent_level, const FunctionDecl* fdecl) {
    // Make a code string that follows this pattern:
    //
    // if (ret) {
    //    new (ret) (return_type) ((class_name*)obj)->func(args...);
    // }
    // else {
    //    ((class_name*)obj)->func(args...);
    // }
    //
    if (const CXXConstructorDecl* CD = dyn_cast<CXXConstructorDecl>(fdecl)) {
        (void) CD;
        make_narg_ctor_with_return(N, class_name, buf, indent_level, fdecl);
        return;
    }
    QualType QT = fdecl->getResultType().getCanonicalType();
    if (QT->isVoidType()) {
        std::ostringstream typedefbuf;
        std::ostringstream callbuf;
        for (int i = 0; i < indent_level; ++i) {
            callbuf << indent_string;
        }
        make_narg_call(N, typedefbuf, callbuf, class_name, indent_level, fdecl);
        callbuf << ";\n";
        for (int i = 0; i < indent_level; ++i) {
            callbuf << indent_string;
        }
        callbuf << "return;\n";
        buf << typedefbuf.str() << callbuf.str();
    }
    else {
        for (int i = 0; i < indent_level; ++i) {
            buf << indent_string;
        }
        buf << "if (ret) {\n";
        ++indent_level;
        {
            std::ostringstream typedefbuf;
            std::ostringstream callbuf;
            //
            //  Write the placement part of the placement new.
            //
            for (int i = 0; i < indent_level; ++i) {
                callbuf << indent_string;
            }
            callbuf << "new (ret) ";
            std::string type_name;
            bool isReference = false;
            int ptrCnt = 0;
            collect_type_info(QT, typedefbuf, callbuf, type_name,
                              isReference, ptrCnt, indent_level, false, fdecl);
            //
            //  Write the type part of the placement new.
            //
            if (isReference) {
                std::string stars;
                for (int j = 0; j < ptrCnt; ++j) {
                    stars.push_back('*');
                }
                callbuf << "(" << type_name.c_str() << stars << "*) (&";
            }
            else if (ptrCnt) {
                std::string stars;
                for (int j = 0; j < ptrCnt; ++j) {
                    stars.push_back('*');
                }
                callbuf << "(" << type_name.c_str() << stars << ") (";
            }
            else {
                callbuf << "(" << type_name.c_str() << ") (";
            }
            //
            //  Write the actual function call.
            //
            make_narg_call(N, typedefbuf, callbuf, class_name, indent_level, fdecl);
            //
            //  End the placement new.
            //
            callbuf << ");\n";
            for (int i = 0; i < indent_level; ++i) {
                callbuf << indent_string;
            }
            callbuf << "return;\n";
            //
            //  Output the whole placement new expression and return statement.
            //
            buf << typedefbuf.str() << callbuf.str();
        }
        --indent_level;
        for (int i = 0; i < indent_level; ++i) {
            buf << indent_string;
        }
        buf << "}\n";
        for (int i = 0; i < indent_level; ++i) {
            buf << indent_string;
        }
        buf << "else {\n";
        ++indent_level;
        {
            std::ostringstream typedefbuf;
            std::ostringstream callbuf;
            for (int i = 0; i < indent_level; ++i) {
                callbuf << indent_string;
            }
            make_narg_call(N, typedefbuf, callbuf, class_name, indent_level, fdecl);
            callbuf << ";\n";
            for (int i = 0; i < indent_level; ++i) {
                callbuf << indent_string;
            }
            callbuf << "return;\n";
            buf << typedefbuf.str() << callbuf.str();
        }
        --indent_level;
        for (int i = 0; i < indent_level; ++i) {
            buf << indent_string;
        }
        buf << "}\n";
    }
}

static CPPYY_Cling_Wrapper_t make_wrapper(const FunctionDecl* fdecl) {
    ASTContext& Context = fdecl->getASTContext();
    PrintingPolicy Policy(Context.getPrintingPolicy());
    //
    //  Get the class or namespace name.
    //
    std::string class_name;
    //    if (const TypeDecl* TD = llvm::dyn_cast<TypeDecl>(fdecl->getDeclContext())) {
    //        // This is a class, struct, or union member.
    //        QualType QT(TD->getTypeForDecl(), 0);
    //        ROOT::TMetaUtils::GetFullyQualifiedTypeName(class_name, QT, *gCppyy_Cling);
    //        // And drop the default arguments if any (at least until the clang
    //        // type printer properly handle template paratemeter that are enumerator).
    //        R__DropDefaultArg(class_name);
    //    }
    //    else
    if (const NamedDecl* ND = llvm::dyn_cast<NamedDecl>(fdecl->getDeclContext())) {
        // This is a namespace member.
        llvm::raw_string_ostream stream(class_name);
        ND->getNameForDiagnostic(stream, Policy, /*Qualified=*/true);
        stream.flush();
    }
    //
    //  Check to make sure that we can
    //  instantiate and codegen this function.
    //
    bool needInstantiation = false;
    const FunctionDecl* Definition = 0;
    if (!fdecl->isDefined(Definition)) {
        FunctionDecl::TemplatedKind TK = fdecl->getTemplatedKind();
        switch (TK) {
        case FunctionDecl::TK_NonTemplate: {
            // Ordinary function, not a template specialization.
            // Note: This might be ok, the body might be defined
            //       in a library, and all we have seen is the
            //       header file.
            //print_error("make_wrapper",
            //    "cannot make wrapper for a function which is declared but not defined!");
            //return 0;
            break;
        }
        case FunctionDecl::TK_FunctionTemplate: {
            // This decl is actually a function template,
            // not a function at all.
            print_error("make_wrapper", "cannot make wrapper for a function template!");
            return 0;
        }
        case FunctionDecl::TK_MemberSpecialization: {
            // This function is the result of instantiating an ordinary
            // member function of a class template, or of instantiating
            // an ordinary member function of a class member of a class
            // template, or of specializing a member function template
            // of a class template, or of specializing a member function
            // template of a class member of a class template.
            if (!fdecl->isTemplateInstantiation()) {
                // We are either TSK_Undeclared or
                // TSK_ExplicitSpecialization.
                // Note: This might be ok, the body might be defined
                //       in a library, and all we have seen is the
                //       header file.
                //print_error("make_wrapper",
                //    "cannot make wrapper for a function template explicit specialization"
                //    " which is declared but not defined!");
                //return 0;
                break;
            }
            const FunctionDecl* Pattern = fdecl->getTemplateInstantiationPattern();
            if (!Pattern) {
                print_error("make_wrapper",
                    "cannot make wrapper for a member function instantiation with no pattern!");
                return 0;
            }
            FunctionDecl::TemplatedKind PTK = Pattern->getTemplatedKind();
            TemplateSpecializationKind PTSK =
                Pattern->getTemplateSpecializationKind();
            if (
                // The pattern is an ordinary member function.
                (PTK == FunctionDecl::TK_NonTemplate) || 
                // The pattern is an explicit specialization, and
                // so is not a template.
                ((PTK != FunctionDecl::TK_FunctionTemplate) &&
                 ((PTSK == TSK_Undeclared) ||
                  (PTSK == TSK_ExplicitSpecialization)))
                ) {
                // Note: This might be ok, the body might be defined
                //       in a library, and all we have seen is the
                //       header file.
                break;
            }
            else if (!Pattern->hasBody()) {
                print_error("make_wrapper",
                    "cannot make wrapper for a member function instantiation with no body!");
                return 0;
            }
            if (fdecl->isImplicitlyInstantiable()) {
                needInstantiation = true;
            }
            break;
        }
        case FunctionDecl::TK_FunctionTemplateSpecialization: {
            // This function is the result of instantiating a function
            // template or possibly an explicit specialization of a
            // function template.  Could be a namespace scope function or a
            // member function.
            if (!fdecl->isTemplateInstantiation()) {
                // We are either TSK_Undeclared or
                // TSK_ExplicitSpecialization.
                // Note: This might be ok, the body might be defined
                //       in a library, and all we have seen is the
                //       header file.
                //print_error("make_wrapper",
                //    "Cannot make wrapper for a function template "
                //    "explicit specialization which is declared but not defined!");
                //return 0;
                break;
            }
            const FunctionDecl* Pattern = fdecl->getTemplateInstantiationPattern();
            if (!Pattern) {
                print_error("make_wrapper",
                    "cannot make wrapper for a function template instantiation with no pattern!");
                return 0;
            }
            FunctionDecl::TemplatedKind PTK = Pattern->getTemplatedKind();
            TemplateSpecializationKind PTSK =
                Pattern->getTemplateSpecializationKind();
            if (
                // The pattern is an ordinary member function.
                (PTK == FunctionDecl::TK_NonTemplate) || 
                // The pattern is an explicit specialization, and
                // so is not a template.
                ((PTK != FunctionDecl::TK_FunctionTemplate) &&
                 ((PTSK == TSK_Undeclared) ||
                  (PTSK == TSK_ExplicitSpecialization)))
                ) {
                // Note: This might be ok, the body might be defined
                //       in a library, and all we have seen is the
                //       header file.
                break;
            }
            if (!Pattern->hasBody()) {
                print_error("make_wrapper",
                    "cannot make wrapper for a function template instantiation with no body!");
                return 0;
            }
            if (fdecl->isImplicitlyInstantiable()) {
                needInstantiation = true;
            }
            break;
        }
        case FunctionDecl::TK_DependentFunctionTemplateSpecialization: {
            // This function is the result of instantiating or
            // specializing a  member function of a class template,
            // or a member function of a class member of a class template,
            // or a member function template of a class template, or a
            // member function template of a class member of a class
            // template where at least some part of the function is
            // dependent on a template argument.
            if (!fdecl->isTemplateInstantiation()) {
                // We are either TSK_Undeclared or
                // TSK_ExplicitSpecialization.
                // Note: This might be ok, the body might be defined
                //       in a library, and all we have seen is the
                //       header file.
                //print_error("make_wrapper",
                //    "Cannot make wrapper for a dependent function template explicit specialization
                //    " which is declared but not defined!");
                //return 0;
                break;
            }
            const FunctionDecl* Pattern = fdecl->getTemplateInstantiationPattern();
            if (!Pattern) {
                print_error("make_wrapper",
                    "cannot make wrapper for a dependent function template instantiation with no pattern!");
                return 0;
            }
            FunctionDecl::TemplatedKind PTK = Pattern->getTemplatedKind();
            TemplateSpecializationKind PTSK =
                Pattern->getTemplateSpecializationKind();
            if (
                // The pattern is an ordinary member function.
                (PTK == FunctionDecl::TK_NonTemplate) || 
                // The pattern is an explicit specialization, and
                // so is not a template.
                ((PTK != FunctionDecl::TK_FunctionTemplate) &&
                 ((PTSK == TSK_Undeclared) ||
                  (PTSK == TSK_ExplicitSpecialization)))
                ) {
                // Note: This might be ok, the body might be defined
                //       in a library, and all we have seen is the
                //       header file.
                break;
            }
            if (!Pattern->hasBody()) {
                print_error("make_wrapper",
                    "cannot make wrapper for a dependent function template instantiation with no body!");
                return 0;
            }
            if (fdecl->isImplicitlyInstantiable()) {
                needInstantiation = true;
            }
            break;
        }
        default: {
            // Will only happen if clang implementation changes.
            // Protect ourselves in case that happens.
            print_error("make_wrapper", "unhandled template kind!");
            return 0;
        }
        }
        // We do not set needInstantiation to true in these cases:
        //
        // isInvalidDecl()
        // TSK_Undeclared
        // TSK_ExplicitInstantiationDefinition
        // TSK_ExplicitSpecialization && !getClassScopeSpecializationPattern()
        // TSK_ExplicitInstantiationDeclaration &&
        //    getTemplateInstantiationPattern() &&
        //    PatternDecl->hasBody() &&
        //    !PatternDecl->isInlined()
        //
        // Set it true in these cases:
        //
        // TSK_ImplicitInstantiation
        // TSK_ExplicitInstantiationDeclaration && (!getPatternDecl() ||
        //    !PatternDecl->hasBody() || PatternDecl->isInlined())
        //
    }
    if (needInstantiation) {
        clang::FunctionDecl* FDmod = const_cast<clang::FunctionDecl*>(fdecl);
        clang::Sema& S = gCppyy_Cling->getSema();
        // Could trigger deserialization of decls.
        cling::Interpreter::PushTransactionRAII RAII(gCppyy_Cling);
        S.InstantiateFunctionDefinition(SourceLocation(), FDmod,
                                        /*Recursive=*/ true,
                                        /*DefinitionRequired=*/ true);
        if (!fdecl->isDefined(Definition)) {
            print_error("make_wrapper", "failed to force template instantiation!");
            return 0;
        }
    }
    if (Definition) {
        FunctionDecl::TemplatedKind TK = Definition->getTemplatedKind();
        switch (TK) {
        case FunctionDecl::TK_NonTemplate: {
            // Ordinary function, not a template specialization.
            if (Definition->isDeleted()) {
                print_error("make_wrapper", "cannot make wrapper for a deleted function!");
                return 0;
            }
            else if (Definition->isLateTemplateParsed()) {
                print_error("make_wrapper",
                    "Cannot make wrapper for a late template parsed function!");
                return 0;
            }
            //else if (Definition->isDefaulted()) {
            //   // Might not have a body, but we can still use it.
            //}
            //else {
            //   // Has a body.
            //}
            break;
        }
        case FunctionDecl::TK_FunctionTemplate: {
            // This decl is actually a function template,
            // not a function at all.
            print_error("make_wrapper", "cannot make wrapper for a function template!");
            return 0;
        }
        case FunctionDecl::TK_MemberSpecialization: {
            // This function is the result of instantiating an ordinary
            // member function of a class template or of a member class
            // of a class template.
            if (Definition->isDeleted()) {
                print_error("make_wrapper",
                    "cannot make wrapper for a deleted member function of a specialization!");
                return 0;
            }
            else if (Definition->isLateTemplateParsed()) {
                print_error("make_wrapper",
                    "cannot make wrapper for a late template parsed member function of a specialization!");
                return 0;
            }
            //else if (Definition->isDefaulted()) {
            //   // Might not have a body, but we can still use it.
            //}
            //else {
            //   // Has a body.
            //}
            break;
        }
        case FunctionDecl::TK_FunctionTemplateSpecialization: {
            // This function is the result of instantiating a function
            // template or possibly an explicit specialization of a
            // function template.  Could be a namespace scope function or a
            // member function.
            if (Definition->isDeleted()) {
                print_error("make_wrapper",
                    "cannot make wrapper for a deleted function template specialization!");
                return 0;
            }
            else if (Definition->isLateTemplateParsed()) {
                print_error("make_wrapper",
                   "cannot make wrapper for a late template parsed function template specialization!");
                return 0;
            }
            //else if (Definition->isDefaulted()) {
            //   // Might not have a body, but we can still use it.
            //}
            //else {
            //   // Has a body.
            //}
            break;
        }
        case FunctionDecl::TK_DependentFunctionTemplateSpecialization: {
            // This function is the result of instantiating or
            // specializing a  member function of a class template,
            // or a member function of a class member of a class template,
            // or a member function template of a class template, or a
            // member function template of a class member of a class
            // template where at least some part of the function is
            // dependent on a template argument.
            if (Definition->isDeleted()) {
                print_error("make_wrapper",
                    "cannot make wrapper for a deleted dependent function template specialization!");
                return 0;
            }
            else if (Definition->isLateTemplateParsed()) {
                print_error("make_wrapper",
                    "cannot make wrapper for a late template parsed "
                    "dependent function template specialization!");
                return 0;
            }
            //else if (Definition->isDefaulted()) {
            //   // Might not have a body, but we can still use it.
            //}
            //else {
            //   // Has a body.
            //}
            break;
        }
        default: {
            // Will only happen if clang implementation changes.
            // Protect ourselves in case that happens.
            print_error("make_wrapper", "unhandled template kind!");
            return 0;
        }
        }
    }
    unsigned min_args = fdecl->getMinRequiredArguments();
    unsigned num_params = fdecl->getNumParams();
    //
    //  Make the wrapper name.
    //
    std::string wrapper_name;
    {
        std::ostringstream buf;
        buf << "__cf";
        //const NamedDecl* ND = llvm::dyn_cast<NamedDecl>(fdecl);
        //std::string mn;
        //gCppyy_Cling->maybeMangleDeclName(ND, mn);
        //buf << '_' << mn;
        buf << '_' << wrapper_serial++;
        wrapper_name = buf.str();
    }
    //
    //  Write the wrapper code.
    // FIXME: this should be synthesized into the AST!
    //
    int indent_level = 0;
    std::ostringstream buf;
    buf << "__attribute__((used)) ";
    buf << "extern \"C\" void ";
    buf << wrapper_name;
    buf << "(void* obj, int nargs, void** args, void* ret)\n";
    buf << "{\n";
    ++indent_level;
    if (min_args == num_params) {
        // No parameters with defaults.
        make_narg_call_with_return(num_params, class_name, buf, indent_level, fdecl);
    }
    else {
        // We need one function call clause compiled for every
        // possible number of arguments per call.
        for (unsigned N = min_args; N <= num_params; ++N) {
            for (int i = 0; i < indent_level; ++i) {
                buf << indent_string;
            }
            buf << "if (nargs == " << N << ") {\n";
            ++indent_level;
            make_narg_call_with_return(N, class_name, buf, indent_level, fdecl);
            --indent_level;
            for (int i = 0; i < indent_level; ++i) {
                buf << indent_string;
            }
            buf << "}\n";
        }
    }
    --indent_level;
    buf << "}\n";
    //
    //  Compile the wrapper code.
    //
    std::string wrapper_code(buf.str());
    std::cout << "   CREATED WRAPPER: " << std::endl;
    std::cout << wrapper_code << std::endl;
    void* wrapper = gCppyy_Cling->compileFunction(
        wrapper_name, wrapper_code, false /*ifUnique*/, true /*withAcessControl*/);
    if (wrapper)
        s_wrappers.insert(std::make_pair((cppyy_method_t)fdecl, (CPPYY_Cling_Wrapper_t)wrapper));
    return (CPPYY_Cling_Wrapper_t)wrapper;
}
