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

#include "Api.h"

#include <iostream>

TClass *TClass::GetClass(const char*, Bool_t, Bool_t) {
   static TClass dummy("dummy");
   return &dummy;
}

class TTestApplication : public TApplication {
public:
    TTestApplication(
        const char* acn, Int_t* argc, char** argv, Bool_t bLoadLibs = kTRUE);
    virtual ~TTestApplication();
};

TTestApplication::TTestApplication(
        const char* acn, int* argc, char** argv, bool do_load) : TApplication(acn, argc, argv) {
    if (do_load) {
        // follow TRint to minimize differences with CINT
        ProcessLine("#include <iostream>", kTRUE);
        ProcessLine("#include <_string>",  kTRUE); // for std::string iostream.
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
}

TTestApplication::~TTestApplication() {}

static const char* appname = "pypy-cppyy";

Bench02RootApp::Bench02RootApp() {
    if (!gApplication) {
        int argc = 1;
        char* argv[1]; argv[0] = (char*)appname;
        gApplication = new TTestApplication(appname, &argc, argv, kFALSE);
    }
}

Bench02RootApp::~Bench02RootApp() {
    // TODO: ROOT globals cleanup ... (?)
}

void Bench02RootApp::report() {
    std::cout << "gROOT is: " << gROOT << std::endl;
    std::cout << "gApplication is: " << gApplication << std::endl;
}

void Bench02RootApp::close_file(TFile* f) {
    std::cout << "closing file " << f->GetName() << " ... " << std::endl;
    f->Write();
    f->Close();
    std::cout << "... file closed" << std::endl;
}
