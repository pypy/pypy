#include "llvm/ADT/SmallPtrSet.h"
#include "llvm/CodeGen/AsmPrinter.h"
#include "llvm/CodeGen/GCMetadataPrinter.h"
#include "llvm/CodeGen/GCStrategy.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/DataLayout.h"
#include "llvm/IR/DerivedTypes.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Type.h"
#include "llvm/MC/MCContext.h"
#include "llvm/MC/MCExpr.h"
#include "llvm/MC/MCStreamer.h"
#include "llvm/Target/TargetLoweringObjectFile.h"
#include "llvm/Target/TargetMachine.h"
#include <vector>

using namespace llvm;


namespace {
  class LLVM_LIBRARY_VISIBILITY PyPyGCStrategy : public GCStrategy {
  public:
    PyPyGCStrategy() {
      UsesMetadata = true;
      NeededSafePoints = 1 << GC::PostCall;
    }
  };
  static GCRegistry::Add<PyPyGCStrategy> X("pypy", "PyPy framework GC");

  class LLVM_LIBRARY_VISIBILITY PyPyGCMetadataPrinter : public GCMetadataPrinter {
  public:
    virtual void finishAssembly(AsmPrinter &AP);
  };
  static GCMetadataPrinterRegistry::Add<PyPyGCMetadataPrinter>
      Y("pypy", "PyPy framework GC");
}

void PyPyGCMetadataPrinter::finishAssembly(AsmPrinter &AP) {
  typedef std::pair<MCSymbol *, MCSymbol *> GCMapEntry;
  std::vector<GCMapEntry> GCMap;
  unsigned PtrSize = AP.TM.getDataLayout()->getPointerSize();

  SmallPtrSet<const Function*, 8> GCStackBottoms;
  const GlobalVariable *GV = getModule().getGlobalVariable("gc_stack_bottoms");
  const ConstantArray *Inits = dyn_cast<ConstantArray>(GV->getInitializer());
  for (unsigned i = 0, e = Inits->getNumOperands(); i != e; ++i)
    if (const Function *F =
          dyn_cast<Function>(Inits->getOperand(i)->stripPointerCasts()))
      GCStackBottoms.insert(F);

  //TODO: switch to read only section
  AP.OutStreamer.SwitchSection(AP.getObjFileLowering().getDataSection());
  AP.EmitAlignment(PtrSize == 4 ? 2 : 3);

  for (iterator I = begin(), IE = end(); I != IE; ++I) {
    GCFunctionInfo &FI = **I;
    uint64_t FrameSize = FI.getFrameSize();
    if (GCStackBottoms.count(&FI.getFunction())) {
      FrameSize |= 1;
    }
    for (GCFunctionInfo::iterator J = FI.begin(), JE = FI.end(); J != JE; ++J) {
      GCPoint &P = *J;
      MCSymbol *ShapeSymbol = AP.OutContext.CreateTempSymbol();
      GCMap.push_back(GCMapEntry(P.Label, ShapeSymbol));
      AP.OutStreamer.EmitLabel(ShapeSymbol);
      AP.OutStreamer.EmitIntValue(FrameSize, PtrSize);
      AP.OutStreamer.EmitIntValue(FI.live_size(J), PtrSize);
      for (GCFunctionInfo::live_iterator K = FI.live_begin(J), KE = FI.live_end(J); K != KE; ++K) {
        AP.OutStreamer.EmitIntValue(K->StackOffset, PtrSize);
      }
    }
  }


  AP.OutStreamer.EmitLabel(AP.OutContext.GetOrCreateSymbol((StringRef) "__gcmap"));
  AP.OutStreamer.EmitIntValue(GCMap.size(), PtrSize);
  for (std::vector<GCMapEntry>::iterator K = GCMap.begin(), KE = GCMap.end(); K != KE; ++K) {
    AP.OutStreamer.EmitValue(MCSymbolRefExpr::Create(K->first, AP.OutContext), PtrSize);
    AP.OutStreamer.EmitValue(MCSymbolRefExpr::Create(K->second, AP.OutContext), PtrSize);
  }
}
