#include "bench02.h"
#include "TROOT.h"
#include "TApplication.h"
#include "TDirectory.h"

#include <iostream>

CloserHack::CloserHack() {
   std::cout << "gROOT is: " << gROOT << std::endl;
   std::cout << "gApplication is: " << gApplication << std::endl;
}

CloserHack::~CloserHack() {
   std::cout << "closing file ... " << std::endl;
   if (gDirectory && gDirectory != gROOT) {
       gDirectory->Write();
       gDirectory->Close();
   }
}

