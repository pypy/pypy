#include "TCanvas.h"
#include "TFile.h"
#include "TProfile.h"
#include "TNtuple.h"
#include "TH1F.h"
#include "TH2F.h"

#include "TROOT.h"
#include "TApplication.h"


class CloserHack {
public:
   CloserHack();
   ~CloserHack();

   void report();
   void close();
};

/*
gROOT      = cppyy.gbl.gROOT
gBenchmark = cppyy.gbl.gBenchmark
gRandom    = cppyy.gbl.gRandom
gSystem    = cppyy.gbl.gSystem
*/
