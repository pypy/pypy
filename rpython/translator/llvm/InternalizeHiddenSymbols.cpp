#include "llvm/IR/LegacyPassManager.h"
#include "llvm/IR/Module.h"
#include "llvm/Transforms/IPO/PassManagerBuilder.h"

using namespace llvm;

namespace {
struct InternalizeHiddenSymbols : public ModulePass {
  static char ID;

  InternalizeHiddenSymbols() : ModulePass(ID) {}

  void getAnalysisUsage(AnalysisUsage &AU) const override {}

  bool runOnModule(Module &M) override;

  const char *getPassName() const override {
    return "Set internal linkage on hidden symbols.";
  }
};
}

char InternalizeHiddenSymbols::ID = 0;

static bool InternalizeIfHidden(GlobalValue &GV) {
  if (GV.getVisibility() != GlobalValue::HiddenVisibility)
    return false;
  GV.setLinkage(GlobalValue::InternalLinkage);
  return true;
}

bool InternalizeHiddenSymbols::runOnModule(Module &M) {
  bool Changed = false;

  for (auto &GV : M.globals())
    Changed |= InternalizeIfHidden(GV);
  for (auto &F : M.functions())
    Changed |= InternalizeIfHidden(F);

  return Changed;
}

static RegisterStandardPasses RegisterMyPass(
    PassManagerBuilder::EP_ModuleOptimizerEarly,
    [](const PassManagerBuilder &Builder, legacy::PassManagerBase &PM) {
      PM.add(new InternalizeHiddenSymbols());
    });
