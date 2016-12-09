// Bindings
#include "capi.h"
#include "cpp_cppyy.h"
#include "callcontext.h"

// ROOT
#include "TBaseClass.h"
#include "TClass.h"
#include "TClassRef.h"
#include "TClassTable.h"
#include "TClassEdit.h"
#include "TCollection.h"
#include "TDataMember.h"
#include "TDataType.h"
#include "TError.h"
#include "TFunction.h"
#include "TGlobal.h"
#include "TInterpreter.h"
#include "TList.h"
#include "TMethod.h"
#include "TMethodArg.h"
#include "TROOT.h"
#include "TSystem.h"

// Standard
#include <assert.h>
#include <algorithm>     // for std::count
#include <dlfcn.h>
#include <map>
#include <set>
#include <sstream>
#include <stdlib.h>      // for getenv

// temp
#include <iostream>
typedef PyROOT::TParameter TParameter;
// --temp


// small number that allows use of stack for argument passing
const int SMALL_ARGS_N = 8;

// data for life time management ---------------------------------------------
typedef std::vector< TClassRef > ClassRefs_t;
static ClassRefs_t g_classrefs( 1 );
static const ClassRefs_t::size_type GLOBAL_HANDLE = 1;

typedef std::map< std::string, ClassRefs_t::size_type > Name2ClassRefIndex_t;
static Name2ClassRefIndex_t g_name2classrefidx;

typedef std::map< Cppyy::TCppMethod_t, CallFunc_t* > Method2CallFunc_t;
static Method2CallFunc_t g_method2callfunc;

typedef std::vector< TGlobal* > GlobalVars_t;
static GlobalVars_t g_globalvars;

// data ----------------------------------------------------------------------
Cppyy::TCppScope_t Cppyy::gGlobalScope = GLOBAL_HANDLE;

// smart pointer types
static std::set< std::string > gSmartPtrTypes =
   { "auto_ptr", "shared_ptr", "weak_ptr", "unique_ptr" };

// configuration
static bool gEnableFastPath = true;


// global initialization -----------------------------------------------------
namespace {

class ApplicationStarter {
public:
   ApplicationStarter() {
      // setup dummy holders for global and std namespaces
      assert( g_classrefs.size() == GLOBAL_HANDLE );
      g_name2classrefidx[ "" ]      = GLOBAL_HANDLE;
      g_classrefs.push_back(TClassRef(""));
      // aliases for std (setup already in pythonify)
      g_name2classrefidx[ "std" ]   = GLOBAL_HANDLE+1;
      g_name2classrefidx[ "::std" ] = GLOBAL_HANDLE+1;
      g_classrefs.push_back(TClassRef("std"));
      // add a dummy global to refer to as null at index 0
      g_globalvars.push_back( nullptr );
      // disable fast path if requested
      if (getenv("CPPYY_DISABLE_FASTPATH")) gEnableFastPath = false;
   }

   ~ApplicationStarter() {
      for ( auto ifunc : g_method2callfunc )
         gInterpreter->CallFunc_Delete( ifunc.second );
   }
} _applicationStarter;

} // unnamed namespace

// local helpers -------------------------------------------------------------
static inline
TClassRef& type_from_handle( Cppyy::TCppScope_t scope )
{
   assert( (ClassRefs_t::size_type) scope < g_classrefs.size() );
   return g_classrefs[ (ClassRefs_t::size_type)scope ];
}

// type_from_handle to go here
static inline
TFunction* type_get_method( Cppyy::TCppType_t klass, Cppyy::TCppIndex_t idx )
{
   TClassRef& cr = type_from_handle( klass );
   if ( cr.GetClass() )
      return (TFunction*)cr->GetListOfMethods()->At( idx );
   assert( klass == (Cppyy::TCppType_t)GLOBAL_HANDLE );
   return (TFunction*)idx;
}

static inline
Cppyy::TCppScope_t declaring_scope( Cppyy::TCppMethod_t method )
{
   TMethod* m = dynamic_cast<TMethod*>( (TFunction*)method );
   if ( m ) return Cppyy::GetScope( m->GetClass()->GetName() );
   return (Cppyy::TCppScope_t)GLOBAL_HANDLE;
}

static inline
char* cppstring_to_cstring( const std::string& cppstr ) {
   char* cstr = (char*)malloc( cppstr.size() + 1 );
   memcpy( cstr, cppstr.c_str(), cppstr.size() + 1 );
   return cstr;
}


// name to opaque C++ scope representation -----------------------------------
Cppyy::TCppIndex_t Cppyy::GetNumScopes( TCppScope_t scope )
{
   TClassRef& cr = type_from_handle( scope );
   if ( cr.GetClass() ) {
   // this is expensive, but this function is only ever called for __dir__
   // TODO: rewrite __dir__ on the C++ side for a single loop
       std::string s = GetFinalName( scope ); s += "::";
       gClassTable->Init(); 
       const int N = gClassTable->Classes();
       int total = 0;
       for ( int i = 0; i < N; ++i ) {
           if ( strncmp( gClassTable->Next(), s.c_str(), s.size() ) == 0 )
              total += 1;
       }
       return total;
   }
   assert( scope == (TCppScope_t)GLOBAL_HANDLE );
   return gClassTable->Classes();
}

std::string Cppyy::GetScopeName( TCppScope_t parent, TCppIndex_t iscope )
{
// Retrieve the scope name of the scope indexed with iscope in parent.
   TClassRef& cr = type_from_handle( parent );
   if ( cr.GetClass() ) {
   // this is expensive (quadratic in number of classes), but only ever called for __dir__
   // TODO: rewrite __dir__ on the C++ side for a single loop
       std::string s = GetFinalName( parent ); s += "::";
       gClassTable->Init();
       const int N = gClassTable->Classes();
       int match = 0;
       for ( int i = 0; i < N; ++i ) {
           char* cname = gClassTable->Next();
           if ( strncmp( cname, s.c_str(), s.size() ) == 0 && match++ == iscope ) {
              std::string ret( cname+ s.size() );
              return ret.substr(0, ret.find( "::" ) ); // TODO: may mean duplicates
           }
       }
       // should never get here ... fall through will fail on assert below
   }
   assert( parent == (TCppScope_t)GLOBAL_HANDLE );
   std::string name = gClassTable->At( iscope );
   if ( name.find("::") == std::string::npos )
       return name;
   return "";
}

std::string Cppyy::ResolveName( const std::string& cppitem_name )
{
// Fully resolve the given name to the final type name.
   std::string tclean = TClassEdit::CleanType( cppitem_name.c_str() );

   TDataType* dt = gROOT->GetType( tclean.c_str() );
   if ( dt ) return dt->GetFullTypeName();
   return TClassEdit::ResolveTypedef( tclean.c_str(), true );
}

Cppyy::TCppScope_t Cppyy::GetScope( const std::string& sname )
{
   std::string scope_name;
   if ( sname.find( "std::", 0, 5 ) == 0 )
      scope_name = sname.substr( 5, std::string::npos );
   else
      scope_name = sname;

   scope_name = ResolveName( scope_name );
   auto icr = g_name2classrefidx.find( scope_name );
   if ( icr != g_name2classrefidx.end() )
      return (TCppType_t)icr->second;

// use TClass directly, to enable auto-loading; class may be stubbed (eg. for
// function returns) leading to a non-null TClass that is otherwise invalid
   TClassRef cr( TClass::GetClass( scope_name.c_str(), kTRUE, kTRUE ) );
   if ( !cr.GetClass() || !cr->Property() )
      return (TCppScope_t)NULL;

   // no check for ClassInfo as forward declared classes are okay (fragile)

   ClassRefs_t::size_type sz = g_classrefs.size();
   g_name2classrefidx[ scope_name ] = sz;
   g_classrefs.push_back( TClassRef( scope_name.c_str() ) );
   return (TCppScope_t)sz;
}

Bool_t Cppyy::IsTemplate( const std::string& template_name )
{
   return (Bool_t)gInterpreter->CheckClassTemplate( template_name.c_str() );
}

Cppyy::TCppType_t Cppyy::GetActualClass( TCppType_t klass, TCppObject_t obj )
{
   TClassRef& cr = type_from_handle( klass );
   TClass* clActual = cr->GetActualClass( (void*)obj );
   if ( clActual && clActual != cr.GetClass() ) {
      // TODO: lookup through name should not be needed
      return (TCppType_t)GetScope( clActual->GetName() );
   }
   return klass;
}

size_t Cppyy::SizeOf( TCppType_t klass )
{
   TClassRef& cr = type_from_handle( klass );
   if ( cr.GetClass() ) return (size_t)cr->Size();
   return (size_t)0;
}

Bool_t Cppyy::IsBuiltin( const std::string& type_name )
{
    TDataType* dt = gROOT->GetType( TClassEdit::CleanType( type_name.c_str(), 1 ).c_str() );
    if ( dt ) return dt->GetType() != kOther_t;
    return kFALSE;
}

Bool_t Cppyy::IsComplete( const std::string& type_name )
{
// verify whether the dictionary of this class is fully available
   Bool_t b = kFALSE;

   Int_t oldEIL = gErrorIgnoreLevel;
   gErrorIgnoreLevel = 3000;
   TClass* klass = TClass::GetClass( TClassEdit::ShortType( type_name.c_str(), 1 ).c_str() );
   if ( klass && klass->GetClassInfo() )     // works for normal case w/ dict
      b = gInterpreter->ClassInfo_IsLoaded( klass->GetClassInfo() );
   else {      // special case for forward declared classes
      ClassInfo_t* ci = gInterpreter->ClassInfo_Factory( type_name.c_str() );
      if ( ci ) {
         b = gInterpreter->ClassInfo_IsLoaded( ci );
         gInterpreter->ClassInfo_Delete( ci );    // we own the fresh class info
      }
   }
   gErrorIgnoreLevel = oldEIL;
   return b;
}

// memory management ---------------------------------------------------------
Cppyy::TCppObject_t Cppyy::Allocate( TCppType_t type )
{
   TClassRef& cr = type_from_handle( type );
   return (TCppObject_t)malloc( cr->Size() );
}

void Cppyy::Deallocate( TCppType_t /* type */, TCppObject_t instance )
{
   free( instance );
}

Cppyy::TCppObject_t Cppyy::Construct( TCppType_t type )
{
   TClassRef& cr = type_from_handle( type );
   return (TCppObject_t)cr->New();
}

void Cppyy::Destruct( TCppType_t type, TCppObject_t instance )
{
   TClassRef& cr = type_from_handle( type );
   cr->Destructor( (void*)instance );
}


// method/function dispatching -----------------------------------------------
static inline ClassInfo_t* GetGlobalNamespaceInfo()
{
   static ClassInfo_t* gcl = gInterpreter->ClassInfo_Factory();
   return gcl;
}

static CallFunc_t* GetCallFunc( Cppyy::TCppMethod_t method )
{
   auto icf = g_method2callfunc.find( method );
   if ( icf != g_method2callfunc.end() )
      return icf->second;

   CallFunc_t* callf = nullptr;
   TFunction* func = (TFunction*)method;
   std::string callString = "";

// create, if not cached
   Cppyy::TCppScope_t scope = declaring_scope( method );
   const TClassRef& klass = type_from_handle( scope );
   if ( klass.GetClass() || (func && scope == GLOBAL_HANDLE) ) {
      ClassInfo_t* gcl = klass.GetClass() ? klass->GetClassInfo() : nullptr;
      if ( ! gcl )
         gcl = GetGlobalNamespaceInfo();

      TCollection* method_args = func->GetListOfMethodArgs();
      TIter iarg( method_args );

      TMethodArg* method_arg = 0;
      while ((method_arg = (TMethodArg*)iarg.Next())) {
         std::string fullType = method_arg->GetTypeNormalizedName();
         if ( callString.empty() )
            callString = fullType;
         else
            callString += ", " + fullType;
      }

      Long_t offset = 0;
      callf = gInterpreter->CallFunc_Factory();

      gInterpreter->CallFunc_SetFuncProto(
         callf,
         gcl,
         func ? func->GetName() : klass->GetName(),
         callString.c_str(),
         func ? (func->Property() & kIsConstMethod) : kFALSE,
         &offset,
         ROOT::kExactMatch );

// CLING WORKAROUND -- The number of arguments is not always correct (e.g. when there
//                     are default parameters, causing the callString to be wrong and
//                     the exact match to fail); or the method may have been inline or
//                     be compiler generated. In all those cases the exact match fails,
//                     whereas the conversion match sometimes works.
      if ( ! gInterpreter->CallFunc_IsValid( callf ) ) {
         gInterpreter->CallFunc_SetFuncProto(
            callf,
            gcl,
            func ? func->GetName() : klass->GetName(),
            callString.c_str(),
            func ? (func->Property() & kIsConstMethod) : kFALSE,
            &offset );  // <- no kExactMatch as that will fail
      }
// -- CLING WORKAROUND

   }

   if ( !( callf && gInterpreter->CallFunc_IsValid( callf ) ) ) {
   // TODO: propagate this error to caller w/o use of Python C-API
   /*
      PyErr_Format( PyExc_RuntimeError, "could not resolve %s::%s(%s)",
         const_cast<TClassRef&>(klass).GetClassName(),
         func ? func->GetName() : const_cast<TClassRef&>(klass).GetClassName(),
         callString.c_str() ); */
      std::cerr << "TODO: report unresolved function error to Python\n";
      if ( callf ) gInterpreter->CallFunc_Delete( callf );
      return nullptr;
   }

   g_method2callfunc[ method ] = callf;
   return callf;
}

static inline void copy_args( void* args_, void** vargs ) {
   std::vector<TParameter>& args = *(std::vector<TParameter>*)args_;
   for ( std::vector<TParameter>::size_type i = 0; i < args.size(); ++i ) {
      switch ( args[i].fTypeCode ) {
      case 'b':          /* bool */
         vargs[i] = (void*)&args[i].fValue.fBool;
         break;
      case 'h':          /* short */
         vargs[i] = (void*)&args[i].fValue.fShort;
         break;
      case 'H':          /* unsigned short */
         vargs[i] = (void*)&args[i].fValue.fUShort;
         break;
      case 'i':          /* int */
         vargs[i] = (void*)&args[i].fValue.fInt;
         break;
      case 'I':          /* unsigned int */
         vargs[i] = (void*)&args[i].fValue.fUInt;
         break;
      case 'l':          /* long */
         vargs[i] = (void*)&args[i].fValue.fLong;
         break;
      case 'L':          /* unsigned long */
         vargs[i] = (void*)&args[i].fValue.fULong;
         break;
      case 'q':          /* long long */
         vargs[i] = (void*)&args[i].fValue.fLongLong;
         break;
      case 'Q':          /* unsigned long long */
         vargs[i] = (void*)&args[i].fValue.fULongLong;
         break;
      case 'f':          /* float */
         vargs[i] = (void*)&args[i].fValue.fFloat;
         break;
      case 'd':          /* double */
         vargs[i] = (void*)&args[i].fValue.fDouble;
         break;
      case 'g':          /* long double */
         vargs[i] = (void*)&args[i].fValue.fLongDouble;
         break;
      case 'a':
      case 'o':
      case 'p':          /* void* */
         vargs[i] = (void*)&args[i].fValue.fVoidp;
         break;
      case 'V':          /* (void*)type& */
         vargs[i] = args[i].fValue.fVoidp;
         break;
      case 'r':          /* const type& */
         vargs[i] = args[i].fRef;
         break;
      default:
         std::cerr << "unknown type code: " << args[i].fTypeCode << std::endl;
         break;
      }
   }
}

Bool_t FastCall(
      Cppyy::TCppMethod_t method, void* args_, void* self, void* result )
{
   const std::vector<TParameter>& args = *(std::vector<TParameter>*)args_;

   CallFunc_t* callf = GetCallFunc( method );
   if ( ! callf )
      return kFALSE;

   TInterpreter::CallFuncIFacePtr_t faceptr = gCling->CallFunc_IFacePtr( callf );
   if ( faceptr.fKind == TInterpreter::CallFuncIFacePtr_t::kGeneric ) {
      if ( args.size() <= SMALL_ARGS_N ) {
         void* smallbuf[SMALL_ARGS_N];
         copy_args( args_, smallbuf );
         faceptr.fGeneric( self, args.size(), smallbuf, result );
      } else {
         std::vector<void*> buf( args.size() );
         copy_args( args_, buf.data() );
         faceptr.fGeneric( self, args.size(), buf.data(), result );
      }
      return kTRUE;
   }

   if ( faceptr.fKind == TInterpreter::CallFuncIFacePtr_t::kCtor ) {
      if ( args.size() <= SMALL_ARGS_N ) {
         void* smallbuf[SMALL_ARGS_N];
         copy_args( args_, (void**)smallbuf );
         faceptr.fCtor( (void**)smallbuf, result, args.size() );
      } else {
         std::vector<void*> buf( args.size() );
         copy_args( args_, buf.data() );
         faceptr.fCtor( buf.data(), result, args.size() );
      }
      return kTRUE;
   }

   if ( faceptr.fKind == TInterpreter::CallFuncIFacePtr_t::kDtor ) {
      std::cerr << " DESTRUCTOR NOT IMPLEMENTED YET! " << std::endl;
      return kFALSE;
   }

   return kFALSE;
}

template< typename T >
static inline T CallT( Cppyy::TCppMethod_t method, Cppyy::TCppObject_t self, void* args )
{
   T t{};
   if ( FastCall( method, args, (void*)self, &t ) )
      return t;
   return (T)-1;
}

#define CPPYY_IMP_CALL( typecode, rtype )                                     \
rtype Cppyy::Call##typecode( TCppMethod_t method, TCppObject_t self, void* args )\
{                                                                            \
   return CallT< rtype >( method, self, args );                              \
}

void Cppyy::CallV( TCppMethod_t method, TCppObject_t self, void* args )
{
   if ( ! FastCall( method, args, (void*)self, nullptr ) )
      return /* TODO ... report error */;
}

CPPYY_IMP_CALL( B,  UChar_t      )
CPPYY_IMP_CALL( C,  Char_t       )
CPPYY_IMP_CALL( H,  Short_t      )
CPPYY_IMP_CALL( I,  Int_t        )
CPPYY_IMP_CALL( L,  Long_t       )
CPPYY_IMP_CALL( LL, Long64_t     )
CPPYY_IMP_CALL( F,  Float_t      )
CPPYY_IMP_CALL( D,  Double_t     )
CPPYY_IMP_CALL( LD, LongDouble_t )

void* Cppyy::CallR( TCppMethod_t method, TCppObject_t self, void* args )
{
   void* r = nullptr;
   if ( FastCall( method, args, (void*)self, &r ) )
      return r;
   return nullptr;
}

Char_t* Cppyy::CallS(
      TCppMethod_t method, TCppObject_t self, void* args, size_t* length )
{
   char* cstr = nullptr;
   TClassRef cr("std::string");
   std::string* cppresult = (std::string*)malloc( sizeof(std::string) );
   if ( FastCall( method, args, self, (void*)cppresult ) ) {
	  cstr = cppstring_to_cstring( *cppresult );
      *length = cppresult->size();
      cppresult->std::string::~string();
   } else
      *length = 0;
   free( (void*)cppresult ); 
   return cstr;
}

Cppyy::TCppObject_t Cppyy::CallConstructor(
      TCppMethod_t method, TCppType_t /* klass */, void* args ) {
   void* obj = nullptr;
   if ( FastCall( method, args, nullptr, &obj ) )
      return (TCppObject_t)obj;
   return (TCppObject_t)0;
}

void Cppyy::CallDestructor( TCppType_t type, TCppObject_t self )
{
   TClassRef& cr = type_from_handle( type );
   cr->Destructor( (void*)self, kTRUE );
}

Cppyy::TCppObject_t Cppyy::CallO( TCppMethod_t method,
      TCppObject_t self, void* args, TCppType_t result_type )
{
   TClassRef& cr = type_from_handle( result_type );
   void* obj = malloc( cr->Size() );
   if ( FastCall( method, args, self, obj ) )
      return (TCppObject_t)obj;
   return (TCppObject_t)0;
}

Cppyy::TCppFuncAddr_t Cppyy::GetFunctionAddress( TCppScope_t scope, TCppIndex_t imeth )
{
   if (!gEnableFastPath) return (TCppFuncAddr_t)nullptr;
   TFunction* f = type_get_method( scope, imeth );
   return (TCppFuncAddr_t)dlsym(RTLD_DEFAULT, f->GetMangledName());
}


// handling of function argument buffer --------------------------------------
void* Cppyy::AllocateFunctionArgs( size_t nargs )
{
   return new TParameter[nargs];
}

void Cppyy::DeallocateFunctionArgs( void* args )
{
   delete [] (TParameter*)args;
}

size_t Cppyy::GetFunctionArgSizeof()
{
   return sizeof( TParameter );
}

size_t Cppyy::GetFunctionArgTypeoffset()
{
   return offsetof( TParameter, fTypeCode );
}


// scope reflection information ----------------------------------------------
Bool_t Cppyy::IsNamespace( TCppScope_t scope ) {
// Test if this scope represents a namespace.
   if ( scope == GLOBAL_HANDLE )
      return kTRUE;
   TClassRef& cr = type_from_handle( scope );
   if ( cr.GetClass() )
      return cr->Property() & kIsNamespace;
   return kFALSE;
}

Bool_t Cppyy::IsAbstract( TCppType_t klass ) {
// Test if this type may not be instantiated.
   TClassRef& cr = type_from_handle( klass );
   if ( cr.GetClass() )
      return cr->Property() & kIsAbstract;
   return kFALSE;
}

Bool_t Cppyy::IsEnum( const std::string& type_name ) {
   if ( type_name.empty() ) return kFALSE;
   return gInterpreter->ClassInfo_IsEnum( type_name.c_str() );
}


// class reflection information ----------------------------------------------
std::string Cppyy::GetFinalName( TCppType_t klass )
{
   if ( klass == GLOBAL_HANDLE )
      return "";
   TClassRef& cr = type_from_handle( klass );
   std::string clName = cr->GetName();
   std::string::size_type pos = clName.substr( 0, clName.find( '<' ) ).rfind( "::" );
   if ( pos != std::string::npos )
      return clName.substr( pos + 2, std::string::npos );
   return clName;
}

std::string Cppyy::GetScopedFinalName( TCppType_t klass )
{
   TClassRef& cr = type_from_handle( klass );
   return cr->GetName();
}

Bool_t Cppyy::HasComplexHierarchy( TCppType_t klass )
{
   int is_complex = 1;
   size_t nbases = 0;

   TClassRef& cr = type_from_handle( klass );
   if ( cr.GetClass() && cr->GetListOfBases() != 0 )
      nbases = GetNumBases( klass );

   if (1 < nbases)
      is_complex = 1;
   else if (nbases == 0)
      is_complex = 0;
   else {         // one base class only
      TBaseClass* base = (TBaseClass*)cr->GetListOfBases()->At( 0 );
      if ( base->Property() & kIsVirtualBase )
         is_complex = 1;       // TODO: verify; can be complex, need not be.
      else
         is_complex = HasComplexHierarchy( GetScope( base->GetName() ) );
   }

   return is_complex;
}

Cppyy::TCppIndex_t Cppyy::GetNumBases( TCppType_t klass )
{
// Get the total number of base classes that this class has.
   TClassRef& cr = type_from_handle( klass );
   if ( cr.GetClass() && cr->GetListOfBases() != 0 )
      return cr->GetListOfBases()->GetSize();
   return 0;
}

std::string Cppyy::GetBaseName( TCppType_t klass, TCppIndex_t ibase )
{
   TClassRef& cr = type_from_handle( klass );
   return ((TBaseClass*)cr->GetListOfBases()->At( ibase ))->GetName();
}

Bool_t Cppyy::IsSubtype( TCppType_t derived, TCppType_t base )
{
   if ( derived == base )
      return kTRUE;
   TClassRef& derived_type = type_from_handle( derived );
   TClassRef& base_type = type_from_handle( base );
   return derived_type->GetBaseClass( base_type ) != 0;
}

void Cppyy::AddSmartPtrType( const std::string& type_name ) {
   gSmartPtrTypes.insert( ResolveName( type_name ) );
}

Bool_t Cppyy::IsSmartPtr( const std::string& type_name ) {
// checks if typename denotes a smart pointer
// TODO: perhaps make this stricter?
   const std::string& real_name = ResolveName( type_name );
   return gSmartPtrTypes.find(
      real_name.substr( 0,real_name.find( "<" ) ) ) != gSmartPtrTypes.end();
}

// type offsets --------------------------------------------------------------
ptrdiff_t Cppyy::GetBaseOffset( TCppType_t derived, TCppType_t base,
      TCppObject_t address, int direction, bool rerror )
{
// calculate offsets between declared and actual type, up-cast: direction > 0; down-cast: direction < 0
   if ( derived == base || !(base && derived) )
      return (ptrdiff_t)0;

   TClassRef& cd = type_from_handle( derived );
   TClassRef& cb = type_from_handle( base );

   if ( !cd.GetClass() || !cb.GetClass() )
      return (ptrdiff_t)0;

   Long_t offset = -1;
   if ( ! (cd->GetClassInfo() && cb->GetClassInfo()) ) {    // gInterpreter requirement
   // would like to warn, but can't quite determine error from intentional
   // hiding by developers, so only cover the case where we really should have
   // had a class info, but apparently don't:
      if ( cd->IsLoaded() ) {
      // warn to allow diagnostics
         std::ostringstream msg;
         msg << "failed offset calculation between " << cb->GetName() << " and " << cd->GetName();
         // TODO: propagate this warning to caller w/o use of Python C-API
         // PyErr_Warn( PyExc_RuntimeWarning, const_cast<char*>( msg.str().c_str() ) );
         std::cerr << "Warning: " << msg << '\n';
      }

   // return -1 to signal caller NOT to apply offset
      return rerror ? (ptrdiff_t)offset : 0;
   }

   offset = gInterpreter->ClassInfo_GetBaseOffset(
      cd->GetClassInfo(), cb->GetClassInfo(), (void*)address, direction > 0 );
   if ( offset == -1 )  // Cling error, treat silently
      return rerror ? (ptrdiff_t)offset : 0;

   return (ptrdiff_t)(direction < 0 ? -offset : offset);
}


// method/function reflection information ------------------------------------
Cppyy::TCppIndex_t Cppyy::GetNumMethods( TCppScope_t scope )
{
   TClassRef& cr = type_from_handle( scope );
   if ( cr.GetClass() && cr->GetListOfMethods() ) {
      Cppyy::TCppIndex_t nMethods = (TCppIndex_t)cr->GetListOfMethods()->GetSize();
      if ( nMethods == (TCppIndex_t)0 ) {
         std::string clName = GetScopedFinalName( scope );
         if ( clName.find( '<' ) != std::string::npos ) {
         // chicken-and-egg problem: TClass does not know about methods until instantiation: force it
            if ( TClass::GetClass( ("std::" + clName).c_str() ) )
               clName = "std::" + clName;
            std::ostringstream stmt;
            stmt << "template class " << clName << ";";
            gInterpreter->Declare( stmt.str().c_str() );
         // now reload the methods
            return (TCppIndex_t)cr->GetListOfMethods( kTRUE )->GetSize();
         }
      }
      return nMethods;
   } else if ( scope == (TCppScope_t)GLOBAL_HANDLE ) {
   // enforce lazines by denying the existence of methods
      return (TCppIndex_t)0;
   }
   return (TCppIndex_t)0;
}

Cppyy::TCppIndex_t Cppyy::GetMethodIndexAt( TCppScope_t scope, TCppIndex_t imeth )
{
   TClassRef& cr = type_from_handle (scope);
   if (cr.GetClass())
      return (TCppIndex_t)imeth;
   assert(scope == (TCppType_t)GLOBAL_HANDLE);
   return imeth;
}

std::vector< Cppyy::TCppMethod_t > Cppyy::GetMethodsFromName(
      TCppScope_t scope, const std::string& name )
{
   std::vector< TCppMethod_t > methods;
   if ( scope == GLOBAL_HANDLE ) {
      // TODO: figure out a way of being conservative with reloading
      TCollection* funcs = gROOT->GetListOfGlobalFunctions( kTRUE );

      // tickle deserialization
      if ( !funcs->FindObject( name.c_str() ) )
         return methods;

      TIter ifunc(funcs);
      TFunction* func = 0;
      while ( (func = (TFunction*)ifunc.Next()) ) {
      // cover not only direct matches, but also template matches
         std::string fn = func->GetName();
         if ( fn.rfind( name, 0 ) == 0 ) {
         // either match exactly, or match the name as template
            if ( (name.size() == fn.size()) ||
                 (name.size() < fn.size() && fn[name.size()] == '<') ) {
               methods.push_back( (TCppMethod_t)func );
            }
         }
      }
   } else {
      TClassRef& cr = type_from_handle( scope );
      if ( cr.GetClass() ) {
      // todo: handle overloads
         TMethod* m = cr->GetMethodAny( name.c_str() );
         if ( m ) methods.push_back( (TCppMethod_t)m );
      }
   }

   return methods;
}

Cppyy::TCppMethod_t Cppyy::GetMethod( TCppScope_t scope, TCppIndex_t imeth )
{
   TFunction* f = type_get_method( scope, imeth );
   return (Cppyy::TCppMethod_t)f;
}

std::string Cppyy::GetMethodName( TCppMethod_t method )
{
   if ( method ) {
      std::string name = ((TFunction*)method)->GetName();
      if ( IsMethodTemplate( method ) )
         return name.substr( 0, name.find('<') );
      return name;
   }
   return "<unknown>";
}

std::string Cppyy::GetMethodResultType( TCppMethod_t method )
{
   if ( method ) {
      TFunction* f = (TFunction*)method;
      if ( f->ExtraProperty() & kIsConstructor )
         return "constructor";
      return f->GetReturnTypeNormalizedName();
   }
   return "<unknown>";
}

Cppyy::TCppIndex_t Cppyy::GetMethodNumArgs( TCppMethod_t method )
{
   if ( method )
      return ((TFunction*)method)->GetNargs();
   return 0;
}

Cppyy::TCppIndex_t Cppyy::GetMethodReqArgs( TCppMethod_t method )
{
   if ( method ) {
      TFunction* f = (TFunction*)method;
      return (TCppIndex_t)(f->GetNargs() - f->GetNargsOpt());
   }
   return (TCppIndex_t)0;
}

std::string Cppyy::GetMethodArgName( TCppMethod_t method, int iarg )
{
   if ( method ) {
      TFunction* f = (TFunction*)method;
      TMethodArg* arg = (TMethodArg*)f->GetListOfMethodArgs()->At( iarg );
      return arg->GetName();
   }
   return "<unknown>";
}

std::string Cppyy::GetMethodArgType( TCppMethod_t method, int iarg )
{
   if ( method ) {
      TFunction* f = (TFunction*)method;
      TMethodArg* arg = (TMethodArg*)f->GetListOfMethodArgs()->At( iarg );
      return arg->GetTypeNormalizedName();
   }
   return "<unknown>";
}

std::string Cppyy::GetMethodArgDefault( TCppMethod_t method, int iarg )
{
   if ( method ) {
      TFunction* f = (TFunction*)method;
      TMethodArg* arg = (TMethodArg*)f->GetListOfMethodArgs()->At( iarg );
      const char* def = arg->GetDefault();
      if ( def )
         return def;
   }

   return "";
}

std::string Cppyy::GetMethodSignature( TCppScope_t scope, TCppIndex_t imeth )
{
   TClassRef& cr = type_from_handle( scope );
   TFunction* f = type_get_method( scope, imeth );
   if ( cr.GetClass() && cr->GetClassInfo() ) {
      std::ostringstream sig;
      sig << f->GetReturnTypeName() << " "
          << cr.GetClassName() << "::" << f->GetName() << "(";
      int nArgs = f->GetNargs();
      for ( int iarg = 0; iarg < nArgs; ++iarg ) {
         sig << ((TMethodArg*)f->GetListOfMethodArgs()->At( iarg ))->GetFullTypeName();
         if (iarg != nArgs-1)
            sig << ", ";
      }
      sig << ")" << std::ends;
      return cppstring_to_cstring(sig.str());
   }
   return "<unknown>";
}

Bool_t Cppyy::IsConstMethod( TCppMethod_t method )
{
   if ( method ) {
      TFunction* f = (TFunction*)method;
      return f->Property() & kIsConstMethod;
   }
   return kFALSE;
}


Bool_t Cppyy::IsMethodTemplate( TCppMethod_t method )
{
   if ( method ) {
      TFunction* f = (TFunction*)method;
      if ( f->ExtraProperty() & kIsConstructor )
         return kFALSE;
      std::string name = f->GetName();
      return (name[name.size()-1] == '>') && (name.find('<') != std::string::npos);
   }
   return kFALSE;
}

Cppyy::TCppIndex_t Cppyy::GetMethodNumTemplateArgs(
      TCppScope_t scope, TCppIndex_t imeth )
{
// this is dumb, but the fact that Cling can instantiate template
// methods on-the-fly means that there is some vast reworking TODO
// in interp_cppyy.py, so this is just to make the original tests
// pass that worked in the Reflex era ...
   const std::string name = GetMethodName(GetMethod(scope, imeth));
   return (TCppIndex_t)(std::count( name.begin(), name.end(), ',' ) + 1);
}

std::string Cppyy::GetMethodTemplateArgName(
      TCppScope_t scope, TCppIndex_t imeth, TCppIndex_t /* iarg */ )
{
// TODO: like above, given Cling's instantiation capability, this
// is just dumb ...
   TClassRef& cr = type_from_handle( scope );
   TFunction* f = type_get_method( scope, imeth );
   std::string name = f->GetName();
   std::string::size_type pos = name.find( '<' );
// TODO: left as-is, this should loop over arguments, but what is here
// suffices to pass the Reflex-based tests (need more tests :) )
   return cppstring_to_cstring(
      ResolveName( name.substr(pos+1, name.size()-pos-2) ) );
}

Cppyy::TCppIndex_t Cppyy::GetGlobalOperator(
      TCppScope_t scope, TCppType_t lc, TCppType_t rc, const std::string& opname )
{
// Find a global operator function with a matching signature
   std::string proto = GetScopedFinalName(lc) + ", " + GetScopedFinalName(rc);
   if ( scope == (cppyy_scope_t)GLOBAL_HANDLE ) {
      TFunction* func = gROOT->GetGlobalFunctionWithPrototype( opname.c_str(), proto.c_str() );
      if (func) return (TCppIndex_t)func;
   } else {
      TClassRef& cr = type_from_handle( scope );
      if ( cr.GetClass() ) {
         TFunction* func = cr->GetMethodWithPrototype( opname.c_str(), proto.c_str() );
         if ( func ) return (TCppIndex_t)cr->GetListOfMethods()->IndexOf( func );
      }
   }

// failure ...
   return (TCppIndex_t)-1;
}

// method properties ---------------------------------------------------------
Bool_t Cppyy::IsConstructor( TCppMethod_t method )
{
   if ( method ) {
      TFunction* f = (TFunction*)method;
      return f->ExtraProperty() & kIsConstructor;
   }
   return kFALSE;
}

Bool_t Cppyy::IsPublicMethod( TCppMethod_t method )
{
   if ( method ) {
      TFunction* f = (TFunction*)method;
      return f->Property() & kIsPublic;
   }
   return kFALSE;
}

Bool_t Cppyy::IsStaticMethod( TCppMethod_t method )
{
   if ( method ) {
      TFunction* f = (TFunction*)method;
      return f->Property() & kIsStatic;
   }
   return kFALSE;
}

// data member reflection information ----------------------------------------
Cppyy::TCppIndex_t Cppyy::GetNumDatamembers( TCppScope_t scope )
{
   TClassRef& cr = type_from_handle( scope );
   if ( cr.GetClass() && cr->GetListOfDataMembers() )
      return cr->GetListOfDataMembers()->GetSize();

// global vars (and unknown classes) are always resolved lazily, so report as '0'
   return (TCppIndex_t)0;
}

std::string Cppyy::GetDatamemberName( TCppScope_t scope, TCppIndex_t idata )
{
   TClassRef& cr = type_from_handle( scope );
   if (cr.GetClass()) {
      TDataMember* m = (TDataMember*)cr->GetListOfDataMembers()->At( idata );
      return m->GetName();
   }
   assert( scope == (TCppScope_t)GLOBAL_HANDLE );
   TGlobal* gbl = g_globalvars[ idata ];
   return gbl->GetName();
}

std::string Cppyy::GetDatamemberType( TCppScope_t scope, TCppIndex_t idata )
{
   if ( scope == GLOBAL_HANDLE ) {
      TGlobal* gbl = g_globalvars[ idata ];
      std::string fullType = gbl->GetFullTypeName();
      if ( fullType[fullType.size()-1] == '*' && \
           !dynamic_cast<TGlobalMappedFunction*>(gbl) && \
           fullType.find( "char", 0, 4 ) == std::string::npos )
         fullType.append( "*" );
      else if ( (int)gbl->GetArrayDim() > 1 )
         fullType.append( "*" );
      else if ( (int)gbl->GetArrayDim() == 1 ) {
         std::ostringstream s;
         s << '[' << gbl->GetMaxIndex( 0 ) << ']' << std::ends;
         fullType.append( s.str() );
      }
      return fullType;
   }

   TClassRef& cr = type_from_handle( scope );
   if ( cr.GetClass() )  {
      TDataMember* m = (TDataMember*)cr->GetListOfDataMembers()->At( idata );
      std::string fullType = m->GetTrueTypeName();
      if ( (int)m->GetArrayDim() > 1 || (!m->IsBasic() && m->IsaPointer()) )
         fullType.append( "*" );
      else if ( (int)m->GetArrayDim() == 1 ) {
         std::ostringstream s;
         s << '[' << m->GetMaxIndex( 0 ) << ']' << std::ends;
         fullType.append( s.str() );
      }
      return fullType;
   }

   return "<unknown>";
}

ptrdiff_t Cppyy::GetDatamemberOffset( TCppScope_t scope, TCppIndex_t idata )
{
   if ( scope == GLOBAL_HANDLE ) {
      TGlobal* gbl = g_globalvars[ idata ];
      return (ptrdiff_t)gbl->GetAddress();
   }

   TClassRef& cr = type_from_handle( scope );
   if ( cr.GetClass() ) {
      TDataMember* m = (TDataMember*)cr->GetListOfDataMembers()->At( idata );
      return (ptrdiff_t)m->GetOffsetCint();      // yes, CINT ...
   }

   return (ptrdiff_t)0;
}

Cppyy::TCppIndex_t Cppyy::GetDatamemberIndex( TCppScope_t scope, const std::string& name )
{
   if ( scope == GLOBAL_HANDLE ) {
      TGlobal* gb = (TGlobal*)gROOT->GetListOfGlobals( kTRUE )->FindObject( name.c_str() );
      if ( gb && gb->GetAddress() && gb->GetAddress() != (void*)-1 ) {
         g_globalvars.push_back( gb );
         return g_globalvars.size() - 1;
      }

   } else {
      TClassRef& cr = type_from_handle( scope );
      if ( cr.GetClass() ) {
         TDataMember* dm =
            (TDataMember*)cr->GetListOfDataMembers()->FindObject( name.c_str() );
         // TODO: turning this into an index is silly ...
         if ( dm ) return (TCppIndex_t)cr->GetListOfDataMembers()->IndexOf( dm );
      }
   }

   return (TCppIndex_t)-1;
}


// data member properties ----------------------------------------------------
Bool_t Cppyy::IsPublicData( TCppScope_t scope, TCppIndex_t idata )
{
   if ( scope == GLOBAL_HANDLE )
      return kTRUE;
   TClassRef& cr = type_from_handle( scope );
   if ( cr->Property() & kIsNamespace )
      return kTRUE;
   TDataMember* m = (TDataMember*)cr->GetListOfDataMembers()->At( idata );
   return m->Property() & kIsPublic;
}

Bool_t Cppyy::IsStaticData( TCppScope_t scope, TCppIndex_t idata  )
{
   if ( scope == GLOBAL_HANDLE )
      return kTRUE;
   TClassRef& cr = type_from_handle( scope );
   if ( cr->Property() & kIsNamespace )
      return kTRUE;
   TDataMember* m = (TDataMember*)cr->GetListOfDataMembers()->At( idata );
   return m->Property() & kIsStatic;
}

Bool_t Cppyy::IsConstData( TCppScope_t scope, TCppIndex_t idata )
{
   if ( scope == GLOBAL_HANDLE ) {
      TGlobal* gbl = g_globalvars[ idata ];
      return gbl->Property() & kIsConstant;
   }
   TClassRef& cr = type_from_handle( scope );
   if ( cr.GetClass() ) {
      TDataMember* m = (TDataMember*)cr->GetListOfDataMembers()->At( idata );
      return m->Property() & kIsConstant;
   }
   return kFALSE;
}

Bool_t Cppyy::IsEnumData( TCppScope_t scope, TCppIndex_t idata )
{
   if ( scope == GLOBAL_HANDLE ) {
      TGlobal* gbl = g_globalvars[ idata ];
      return gbl->Property() & kIsEnum;
   }
   TClassRef& cr = type_from_handle( scope );
   if ( cr.GetClass() ) {
      TDataMember* m = (TDataMember*)cr->GetListOfDataMembers()->At( idata );
      return m->Property() & kIsEnum;
   }
   return kFALSE;
}

Int_t Cppyy::GetDimensionSize( TCppScope_t scope, TCppIndex_t idata, int dimension )
{
   if ( scope == GLOBAL_HANDLE ) {
      TGlobal* gbl = g_globalvars[ idata ];
      return gbl->GetMaxIndex( dimension );
   }
   TClassRef& cr = type_from_handle( scope );
   if ( cr.GetClass() ) {
      TDataMember* m = (TDataMember*)cr->GetListOfDataMembers()->At( idata );
      return m->GetMaxIndex( dimension );
   }
   return (Int_t)-1;
}


static inline
std::vector<TParameter> vsargs_to_parvec(void* args, int nargs)
{
    std::vector<TParameter> v;
    v.reserve(nargs);
    for (int i=0; i<nargs; ++i)
       v.push_back(((TParameter*)args)[i]);
    return v;
}

//- C-linkage wrappers -------------------------------------------------------
extern "C" {
/* name to opaque C++ scope representation -------------------------------- */
int cppyy_num_scopes(cppyy_scope_t parent) {
    return (int)Cppyy::GetNumScopes(parent);
}

char* cppyy_scope_name(cppyy_scope_t parent, int iscope) {
    return cppstring_to_cstring(Cppyy::GetScopeName(parent, iscope));
}

char* cppyy_resolve_name(const char* cppitem_name) {
    std::string str = cppstring_to_cstring(Cppyy::ResolveName(cppitem_name));
    if (Cppyy::IsEnum(str))
        return cppstring_to_cstring("internal_enum_type_t");
    return cppstring_to_cstring(str);
}

cppyy_scope_t cppyy_get_scope(const char* scope_name) {
    return cppyy_scope_t(Cppyy::GetScope(scope_name));
}

cppyy_type_t cppyy_actual_class(cppyy_type_t klass, cppyy_object_t obj) {
    return cppyy_type_t(Cppyy::GetActualClass(klass, (void*)obj));
}


/* memory management ------------------------------------------------------ */
cppyy_object_t cppyy_allocate(cppyy_type_t type) {
    return cppyy_object_t(Cppyy::Allocate(type));
}

void cppyy_deallocate(cppyy_type_t type, cppyy_object_t self) {
    Cppyy::Deallocate(type, (void*)self);
}

void cppyy_destruct(cppyy_type_t type, cppyy_object_t self) {
    Cppyy::Destruct(type, (void*)self);
}


/* method/function dispatching -------------------------------------------- */
void cppyy_call_v(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    std::vector<TParameter> parvec = vsargs_to_parvec(args, nargs);
    Cppyy::CallV(method, (void*)self, &parvec);
}

unsigned char cppyy_call_b(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    std::vector<TParameter> parvec = vsargs_to_parvec(args, nargs);
    return (unsigned char)Cppyy::CallB(method, (void*)self, &parvec);
}

char cppyy_call_c(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    std::vector<TParameter> parvec = vsargs_to_parvec(args, nargs);
    return (char)Cppyy::CallC(method, (void*)self, &parvec);
}

short cppyy_call_h(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    std::vector<TParameter> parvec = vsargs_to_parvec(args, nargs);
    return (short)Cppyy::CallH(method, (void*)self, &parvec);
}

int cppyy_call_i(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    std::vector<TParameter> parvec = vsargs_to_parvec(args, nargs);
    return (int)Cppyy::CallI(method, (void*)self, &parvec);
}

long cppyy_call_l(cppyy_method_t method, cppyy_object_t self, int nargs, void* args){
    std::vector<TParameter> parvec = vsargs_to_parvec(args, nargs);
    return (long)Cppyy::CallL(method, (void*)self, &parvec);
}

long long cppyy_call_ll(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    std::vector<TParameter> parvec = vsargs_to_parvec(args, nargs);
    return (long long)Cppyy::CallLL(method, (void*)self, &parvec);
}

float cppyy_call_f(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    std::vector<TParameter> parvec = vsargs_to_parvec(args, nargs);
    return (float)Cppyy::CallF(method, (void*)self, &parvec);
}

double cppyy_call_d(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    std::vector<TParameter> parvec = vsargs_to_parvec(args, nargs);
    return (double)Cppyy::CallD(method, (void*)self, &parvec);
}

long double cppyy_call_ld(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    std::vector<TParameter> parvec = vsargs_to_parvec(args, nargs);
    return (long double)Cppyy::CallLD(method, (void*)self, &parvec);
}

void* cppyy_call_r(cppyy_method_t method, cppyy_object_t self, int nargs, void* args) {
    std::vector<TParameter> parvec = vsargs_to_parvec(args, nargs);
    return (void*)Cppyy::CallR(method, (void*)self, &parvec);
}

char* cppyy_call_s(
        cppyy_method_t method, cppyy_object_t self, int nargs, void* args, size_t* lsz) {
    std::vector<TParameter> parvec = vsargs_to_parvec(args, nargs);
    return Cppyy::CallS(method, (void*)self, &parvec, lsz);
}

cppyy_object_t cppyy_constructor(cppyy_method_t method, cppyy_type_t klass, int nargs, void* args) {
    std::vector<TParameter> parvec = vsargs_to_parvec(args, nargs);
    return cppyy_object_t(Cppyy::CallConstructor(method, klass, &parvec));
}

cppyy_object_t cppyy_call_o(cppyy_method_t method, cppyy_object_t self, int nargs, void* args, cppyy_type_t result_type) {
    std::vector<TParameter> parvec = vsargs_to_parvec(args, nargs);
    return cppyy_object_t(Cppyy::CallO(method, (void*)self, &parvec, result_type));
}

cppyy_funcaddr_t cppyy_get_function_address(cppyy_scope_t scope, cppyy_index_t idx) {
    return cppyy_funcaddr_t(Cppyy::GetFunctionAddress(scope, idx));
}


/* handling of function argument buffer ----------------------------------- */
void* cppyy_allocate_function_args(int nargs){
    return (void*)Cppyy::AllocateFunctionArgs(nargs);
}

void cppyy_deallocate_function_args(void* args){
    Cppyy::DeallocateFunctionArgs(args);
}

size_t cppyy_function_arg_sizeof(){
    return (size_t)Cppyy::GetFunctionArgSizeof();
}

size_t cppyy_function_arg_typeoffset(){
    return (size_t)Cppyy::GetFunctionArgTypeoffset();
}


/* scope reflection information ------------------------------------------- */
int cppyy_is_namespace(cppyy_scope_t scope) {
    return (int)Cppyy::IsNamespace(scope);
}

int cppyy_is_template(const char* template_name) {
    return (int)Cppyy::IsTemplate(template_name);
}

int cppyy_is_abstract(cppyy_type_t type){
    return (int)Cppyy::IsAbstract(type);
}

int cppyy_is_enum(const char* type_name){
    return (int)Cppyy::IsEnum(type_name);
}


/* class reflection information ------------------------------------------- */
char* cppyy_final_name(cppyy_type_t type) {
    return cppstring_to_cstring(Cppyy::GetFinalName(type));
}

char* cppyy_scoped_final_name(cppyy_type_t type) {
    return cppstring_to_cstring(Cppyy::GetScopedFinalName(type));
}

int cppyy_has_complex_hierarchy(cppyy_type_t type) {
    return (int)Cppyy::HasComplexHierarchy(type);
}

int cppyy_num_bases(cppyy_type_t type) {
    return (int)Cppyy::GetNumBases(type);
}

char* cppyy_base_name(cppyy_type_t type, int base_index){
    return cppstring_to_cstring(Cppyy::GetBaseName (type, base_index));
}

int cppyy_is_subtype(cppyy_type_t derived, cppyy_type_t base){
    return (int)Cppyy::IsSubtype(derived, base);
}


/* calculate offsets between declared and actual type, up-cast: direction > 0; down-cast: direction < 0 */
ptrdiff_t cppyy_base_offset(cppyy_type_t derived, cppyy_type_t base, cppyy_object_t address, int direction) {
    return (ptrdiff_t)Cppyy::GetBaseOffset(derived, base, (void*)address, direction, 0);
}


/* method/function reflection information --------------------------------- */
int cppyy_num_methods(cppyy_scope_t scope) {
    return (int)Cppyy::GetNumMethods(scope);
}

cppyy_index_t cppyy_method_index_at(cppyy_scope_t scope, int imeth) {
    return cppyy_index_t(Cppyy::GetMethodIndexAt(scope, imeth));
}

static inline bool match_name(const std::string& tname, const std::string fname) {
// either match exactly, or match the name as template
   if (fname.rfind(tname, 0) == 0) {
      if ( (tname.size() == fname.size()) ||
           (tname.size() < fname.size() && fname[tname.size()] == '<') )
         return true;
   }
   return false;
}

cppyy_index_t* cppyy_method_indices_from_name(cppyy_scope_t scope, const char* name) {
    std::vector<cppyy_index_t> result;
    TClassRef& cr = type_from_handle(scope);
    if (cr.GetClass()) {
        gInterpreter->UpdateListOfMethods(cr.GetClass());
        int imeth = 0;
        TFunction* func;
        TIter next(cr->GetListOfMethods());
        while ((func = (TFunction*)next())) {
            if (match_name(name, func->GetName())) {
                if (Cppyy::IsPublicMethod((cppyy_method_t)func))
                    result.push_back((cppyy_index_t)imeth);
            }
            ++imeth;
        }
    } else if (scope == (cppyy_scope_t)GLOBAL_HANDLE) {
        TCollection* funcs = gROOT->GetListOfGlobalFunctions(kTRUE);

        // tickle deserialization
        if (!funcs->FindObject(name))
            return (cppyy_index_t*)nullptr;

        TFunction* func = 0;
        TIter ifunc(funcs);
        while ((func = (TFunction*)ifunc.Next())) {
            if (match_name(name, func->GetName()))
                result.push_back((cppyy_index_t)func);
        }
    }

    if (result.empty())
        return (cppyy_index_t*)nullptr;

    cppyy_index_t* llresult = (cppyy_index_t*)malloc(sizeof(cppyy_index_t)*(result.size()+1));
    for (int i = 0; i < (int)result.size(); ++i) llresult[i] = result[i];
    llresult[result.size()] = -1;
    return llresult;
}

char* cppyy_method_name(cppyy_scope_t scope, cppyy_index_t idx) {
    TFunction* f = type_get_method(scope, idx);
    return cppstring_to_cstring(Cppyy::GetMethodName((Cppyy::TCppMethod_t)f));
}

char* cppyy_method_result_type(cppyy_scope_t scope, cppyy_index_t idx) {
    TFunction* f = type_get_method(scope, idx);
    return cppstring_to_cstring(Cppyy::GetMethodResultType((Cppyy::TCppMethod_t)f));
}

int cppyy_method_num_args(cppyy_scope_t scope, cppyy_index_t idx) {
    TFunction* f = type_get_method(scope, idx);
    return (int)Cppyy::GetMethodNumArgs((Cppyy::TCppMethod_t)f);
}

int cppyy_method_req_args(cppyy_scope_t scope, cppyy_index_t idx) {
    TFunction* f = type_get_method(scope, idx);
    return (int)Cppyy::GetMethodReqArgs((Cppyy::TCppMethod_t)f);
}

char* cppyy_method_arg_type(cppyy_scope_t scope, cppyy_index_t idx, int arg_index) {
    TFunction* f = type_get_method(scope, idx);
    return cppstring_to_cstring(Cppyy::GetMethodArgType((Cppyy::TCppMethod_t)f, arg_index));
}

char* cppyy_method_arg_default(cppyy_scope_t scope, cppyy_index_t idx, int arg_index) {
    TFunction* f = type_get_method(scope, idx);
    return cppstring_to_cstring(Cppyy::GetMethodArgDefault((Cppyy::TCppMethod_t)f, arg_index));
}

char* cppyy_method_signature(cppyy_scope_t scope, cppyy_index_t idx) {
    return cppstring_to_cstring(Cppyy::GetMethodSignature(scope, idx));
}

int cppyy_method_is_template(cppyy_scope_t scope, cppyy_index_t idx) {
    TFunction* f = type_get_method(scope, idx);
    return (int)Cppyy::IsMethodTemplate((Cppyy::TCppMethod_t)f);
}

int cppyy_method_num_template_args(cppyy_scope_t scope, cppyy_index_t idx) {
    return (int)Cppyy::GetMethodNumTemplateArgs(scope, idx);
}

char* cppyy_method_template_arg_name(cppyy_scope_t scope, cppyy_index_t idx, cppyy_index_t iarg) {
    return cppstring_to_cstring(Cppyy::GetMethodTemplateArgName(scope, idx, iarg));
}

cppyy_method_t cppyy_get_method(cppyy_scope_t scope, cppyy_index_t idx) {
    return cppyy_method_t(Cppyy::GetMethod(scope, idx));
}

cppyy_index_t cppyy_get_global_operator(cppyy_scope_t scope, cppyy_scope_t lc, cppyy_scope_t rc, const char* op) {
    return cppyy_index_t(Cppyy::GetGlobalOperator(scope, lc, rc, op));
}


/* method properties ------------------------------------------------------ */
int cppyy_is_constructor(cppyy_type_t type, cppyy_index_t idx) {
    TFunction* f = type_get_method(type, idx);
    return (int)Cppyy::IsConstructor((Cppyy::TCppMethod_t)f);
}

int cppyy_is_staticmethod(cppyy_type_t type, cppyy_index_t idx) {
    TFunction* f = type_get_method(type, idx);
    return (int)Cppyy::IsStaticMethod((Cppyy::TCppMethod_t)f);
}


/* data member reflection information ------------------------------------- */
int cppyy_num_datamembers(cppyy_scope_t scope) {
    return (int)Cppyy::GetNumDatamembers(scope);
}

char* cppyy_datamember_name(cppyy_scope_t scope, int datamember_index) {
    return cppstring_to_cstring(Cppyy::GetDatamemberName(scope, datamember_index));
}

char* cppyy_datamember_type(cppyy_scope_t scope, int datamember_index) {
    return cppstring_to_cstring(Cppyy::GetDatamemberType(scope, datamember_index));
}

ptrdiff_t cppyy_datamember_offset(cppyy_scope_t scope, int datamember_index) {
    return ptrdiff_t(Cppyy::GetDatamemberOffset(scope, datamember_index));
}

int cppyy_datamember_index(cppyy_scope_t scope, const char* name) {
    return (int)Cppyy::GetDatamemberIndex(scope, name);
}



/* data member properties ------------------------------------------------- */
int cppyy_is_publicdata(cppyy_type_t type, int datamember_index) {
    return (int)Cppyy::IsPublicData(type, datamember_index);
}

int cppyy_is_staticdata(cppyy_type_t type, int datamember_index) {
    return (int)Cppyy::IsStaticData(type, datamember_index);
}


/* misc helpers ----------------------------------------------------------- */
RPY_EXTERN
void* cppyy_load_dictionary(const char* lib_name) {
    int result = gSystem->Load(lib_name);
    return (void*)(result == 0 /* success */ || result == 1 /* already loaded */);
}

long long cppyy_strtoll(const char* str) {
    return strtoll(str, NULL, 0);
}

unsigned long long cppyy_strtoull(const char* str) {
    return strtoull(str, NULL, 0);
}

void cppyy_free(void* ptr) {
    free(ptr);
}

cppyy_object_t cppyy_charp2stdstring(const char* str, size_t sz) {
    return (cppyy_object_t)new std::string(str, sz);
}

const char* cppyy_stdstring2charp(cppyy_object_t ptr, size_t* lsz) {
    *lsz = ((std::string*)ptr)->size();
    return ((std::string*)ptr)->data();
}

cppyy_object_t cppyy_stdstring2stdstring(cppyy_object_t ptr){
    return (cppyy_object_t)new std::string(*(std::string*)ptr);
}

const char* cppyy_stdvector_valuetype(const char* clname) {
    const char* result = nullptr;
    std::string name = clname;
    TypedefInfo_t* ti = gInterpreter->TypedefInfo_Factory((name+"::value_type").c_str());
    if (gInterpreter->TypedefInfo_IsValid(ti))
        result = cppstring_to_cstring(gInterpreter->TypedefInfo_TrueName(ti));
    gInterpreter->TypedefInfo_Delete(ti);
    return result;
}

size_t cppyy_stdvector_valuesize(const char* clname) {
    size_t result = 0;
    std::string name = clname;
    TypedefInfo_t* ti = gInterpreter->TypedefInfo_Factory((name+"::value_type").c_str());
    if (gInterpreter->TypedefInfo_IsValid(ti))
       result = (size_t)gInterpreter->TypedefInfo_Size(ti);
    gInterpreter->TypedefInfo_Delete(ti);
    return result;
}
   
} // end C-linkage wrappers
