#include "TCanvas.h"
#include "TFile.h"
#include "TProfile.h"
#include "TNtuple.h"
#include "TH1F.h"
#include "TH2F.h"
#include "TRandom.h"

#include "TROOT.h"
#include "TApplication.h"

#include "TBox.h"
#include "TClassGenerator.h"
#include "TF1.h"
#include "TFileMergeInfo.h"
#include "TFolder.h"
#include "TFunction.h"
#include "TFrame.h"
#include "TGlobal.h"
#include "TInetAddress.h"
#include "TInterpreter.h"
#include "TKey.h"
#include "TLegend.h"
#include "TPluginManager.h"
#include "TProcessUUID.h"
#include "TStyle.h"
#include "TSysEvtHandler.h"
#include "TTimer.h"
#include "TView.h"
#include "TVirtualFFT.h"
#include "TVirtualHistPainter.h"
#include "TVirtualPadPainter.h"
#include "TVirtualViewer3D.h"

#include <typeinfo>
#include <ostream>


class Bench02RootApp {
public:
   Bench02RootApp();
   ~Bench02RootApp();

   void report();
   void close_file(TFile* f);
};

/*
gROOT      = cppyy.gbl.gROOT
gBenchmark = cppyy.gbl.gBenchmark
gRandom    = cppyy.gbl.gRandom
gSystem    = cppyy.gbl.gSystem
*/
