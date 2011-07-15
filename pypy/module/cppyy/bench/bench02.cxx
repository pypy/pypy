#include "bench02.h"
#include "TROOT.h"
#include "TApplication.h"
#include "TDirectory.h"
#include "TInterpreter.h"
#include "TSystem.h"
#include "TBenchmark.h"
#include "TStyle.h"
#include "TError.h"
#include "Getline.h"
#include "TVirtualX.h"

// CINT
#include "Api.h"

#include <iostream>

class TTestApplication : public TApplication {
public:
   TTestApplication(
      const char* acn, Int_t* argc, char** argv, Bool_t bLoadLibs = kTRUE );

   virtual ~TTestApplication();
};


//- constructors/destructor --------------------------------------------------
TTestApplication::TTestApplication(
   const char* acn, int* argc, char** argv, bool bLoadLibs ) :
      TApplication( acn, argc, argv )
{
// Create a TApplication derived for use with interactive ROOT from python. A
// set of standard, often used libs is loaded if bLoadLibs is true (default).

   if ( bLoadLibs )   // note that this section could be programmed in python
   {
   // follow TRint to minimize differences with CINT
      ProcessLine( "#include <iostream>", kTRUE );
      ProcessLine( "#include <_string>",  kTRUE ); // for std::string iostream.
      ProcessLine( "#include <vector>",   kTRUE ); // needed because they're used within the
      ProcessLine( "#include <pair>",     kTRUE ); //  core ROOT dicts and CINT won't be able
                                                   //  to properly unload these files

   // following RINT, these are now commented out (rely on auto-loading)
   //   // the following libs are also useful to have, make sure they are loaded...
   //      gROOT->LoadClass("TMinuit",     "Minuit");
   //      gROOT->LoadClass("TPostScript", "Postscript");
   //      gROOT->LoadClass("THtml",       "Html");
   }

#ifdef WIN32
   // switch win32 proxy main thread id
   if (gVirtualX)
      ProcessLine("((TGWin32 *)gVirtualX)->SetUserThreadId(0);", kTRUE);
#endif

// save current interpreter context
   gInterpreter->SaveContext();
   gInterpreter->SaveGlobalsContext();

// prevent crashes on accessing histor
   Gl_histinit( (char*)"-" );

// prevent ROOT from exiting python
   SetReturnFromRun( kTRUE );
}

TTestApplication::~TTestApplication() {}

static const char* appname = "pypy-cppyy";

CloserHack::CloserHack() {
   std::cout << "gROOT is: " << gROOT << std::endl;
   std::cout << "gApplication is: " << gApplication << std::endl;

   if ( ! gApplication ) {
   // retrieve arg list from python, translate to raw C, pass on
      int argc = 1;
      char* argv[1]; argv[0] = (char*)appname;
      gApplication = new TTestApplication( appname, &argc, argv, kTRUE );
   }

   std::cout << "gApplication is: " << gApplication << std::endl;
}

void CloserHack::report() {
   std::cout << "gROOT is: " << gROOT << std::endl;
   std::cout << "gApplication is: " << gApplication << std::endl;
}

void CloserHack::close() {
   std::cout << "closing file ... " << std::endl;
   if (gDirectory && gDirectory != gROOT) {
       gDirectory->Write();
       gDirectory->Close();
   }
}

CloserHack::~CloserHack() {
}

