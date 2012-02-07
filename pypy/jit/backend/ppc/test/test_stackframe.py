"""

                PyPy PPC Stackframe

                                                                               OLD  FRAME
            |         BACK CHAIN      |                                        
  - - - - - --------------------------- - - - - -- - - - - - - - - - 
            |                         |          |                             CURRENT FRAME
            |      FPR SAVE AREA      |          |>> len(NONVOLATILES_FPR) * DOUBLEWORD
            |                         |          |
            ---------------------------         --
            |                         |          |
            |      GPR SAVE AREA      |          |>> len(NONVOLATILES) * WORD
            |                         |          |
            ---------------------------         --
            |                         |          |
            |   FLOAT/INT CONVERSION  |          |>> 1 * WORD
            |                         |          |
            ---------------------------         --
            |       FORCE  INDEX      | WORD     |>> 1 WORD
            ---------------------------         --
            |                         |          |
            |      ENCODING AREA      |          |>> len(MANAGED_REGS) * WORD
            |      (ALLOCA AREA)      |          |
    SPP ->  ---------------------------         --
            |                         |          |
            |       SPILLING AREA     |          |>> regalloc.frame_manager.frame_depth * WORD
            |  (LOCAL VARIABLE SPACE) |          |
            ---------------------------         --
            |                         |          |
            |  PARAMETER SAVE AREA    |          |>> max_stack_params * WORD
            |                         |          |
            ---------------------------         --
  (64 Bit)  |        TOC POINTER      | WORD     |
            ---------------------------         --
            |                         |          |
  (64 Bit)  |  RESERVED FOR COMPILER  |          |>> 2 * WORD
            |       AND LINKER        |          |  
            ---------------------------         --
            |         SAVED LR        | WORD     |
            ---------------------------          |>> 3 WORDS (64 Bit)
  (64 Bit)  |         SAVED CR        | WORD     |   2 WORDS (32 Bit)
            ---------------------------          |
            |        BACK CHAIN       | WORD     |
     SP ->  ---------------------------         --


"""
