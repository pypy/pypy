#include "wrapper_cpp.h"
#include <llvm/IR/Instruction.h>
#include <llvm/IR/Instructions.h>
#include <llvm/IR/BasicBlock.h>
#include <llvm/IR/Module.h>
#include <llvm/ADT/APInt.h>
#include <llvm/Support/raw_ostream.h>
#include "llvm/Transforms/Utils/LoopSimplify.h"
#include <llvm/IR/PassManager.h>
#include "llvm/Transforms/Scalar.h"
#include "llvm-c/Initialization.h"
#include "llvm-c/Transforms/Scalar.h"
#include "llvm/Analysis/BasicAliasAnalysis.h"
#include "llvm/Analysis/Passes.h"
#include "llvm/Analysis/ScopedNoAliasAA.h"
#include "llvm/Analysis/TypeBasedAliasAnalysis.h"
#include "llvm/IR/DataLayout.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/IR/Verifier.h"
#include "llvm/InitializePasses.h"
#include "llvm/Transforms/Scalar/GVN.h"
#include "llvm/Transforms/Scalar/Scalarizer.h"
#include "llvm/Transforms/Scalar/SimpleLoopUnswitch.h"
#include "llvm/Transforms/Utils/UnifyFunctionExitNodes.h"
#include "llvm/Transforms/IPO/FunctionAttrs.h"
#include <cstddef>
#include <sys/types.h>
#include <stdio.h>
using namespace llvm;

#ifdef __cplusplus
extern "C"{
#endif
    LLVMTypeRef getResultElementType_wrapper(LLVMValueRef gep_instr){
        GetElementPtrInst *inst = reinterpret_cast<GetElementPtrInst *>(gep_instr);
        return reinterpret_cast<LLVMTypeRef>(inst->getResultElementType());
    }

    LLVMValueRef removeIncomingValue_wrapper(LLVMValueRef phi, LLVMBasicBlockRef block){
        PHINode *phi_node = reinterpret_cast<PHINode *>(phi);
        BasicBlock *basic_block = reinterpret_cast<BasicBlock *>(block);
        return reinterpret_cast<LLVMValueRef>(phi_node->removeIncomingValue(basic_block));
    }

    void removePredecessor_wrapper(LLVMBasicBlockRef current, LLVMBasicBlockRef pred){
        BasicBlock *current_block = reinterpret_cast<BasicBlock *>(current);
        BasicBlock *pred_block = reinterpret_cast<BasicBlock *>(pred);
        current_block->removePredecessor(pred_block, true);
    }

    LLVMValueRef getFirstNonPhi_wrapper(LLVMBasicBlockRef block){
        BasicBlock *basic_block = reinterpret_cast<BasicBlock *>(block);
        return reinterpret_cast<LLVMValueRef>(basic_block->getFirstNonPHI());
    }

    LLVMBasicBlockRef splitBasicBlockAtPhi_wrapper(LLVMBasicBlockRef block){
        BasicBlock *basic_block = reinterpret_cast<BasicBlock *>(block);
        Instruction *I = basic_block->getFirstNonPHI();
        return reinterpret_cast<LLVMBasicBlockRef>(basic_block->splitBasicBlock(I));
    }

    LLVMValueRef getTerminator_wrapper(LLVMBasicBlockRef block){
        BasicBlock *basic_block = reinterpret_cast<BasicBlock *>(block);
        return reinterpret_cast<LLVMValueRef>(basic_block->getTerminator());
    }

    void dumpModule_wrapper(LLVMModuleRef mod){
        std::string str;
        llvm::raw_ostream &output = llvm::errs();
        unwrap(mod)->print(output, NULL);
    }

    void dumpBasicBlock_wrapper(LLVMBasicBlockRef block){
        std::string str;
        llvm::raw_ostream &output = llvm::errs();
        unwrap(block)->print(output, NULL);
    }

    LLVMValueRef getIncomingValueForBlock_wrapper(LLVMValueRef phi, LLVMBasicBlockRef block){
        BasicBlock *basic_block = unwrap(block);
        PHINode *phi_node = cast<PHINode>(unwrap(phi));
        return wrap(phi_node->getIncomingValueForBlock(basic_block));
    }

    void AddLoopSimplifyPass_wrapper(LLVMPassManagerRef pass_manager){
        unwrap(pass_manager)->add(llvm::createLoopSimplifyCFGPass());
    }

    void AddLoopStrengthReducePass_wrapper(LLVMPassManagerRef pass_manager){
        unwrap(pass_manager)->add(llvm::createLoopStrengthReducePass());
    }

    void AddInferFunctionAttrsPass_wrapper(LLVMPassManagerRef pass_manager){
        unwrap(pass_manager)->add(llvm::createPostOrderFunctionAttrsLegacyPass());
    }


#ifdef __cplusplus
}
#endif
