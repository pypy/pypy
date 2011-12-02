"""

                PyPy PPC Stackframe

                                                                               OLD  FRAME
            |         BACK CHAIN      |                                        
  - - - - - --------------------------- - - - - -- - - - - - - - - - 
            |                         |          |                             CURRENT FRAME
            |      FPR SAVE AREA      |          |>> len(NONVOLATILES_FPR) * WORD
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
            |       FORCE  INDEX      | WORD     | 1 WORD
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
            ---------------------------a        --
            |        TOC POINTER      | WORD     |
            ---------------------------          |
            |       < RESERVED >      | WORD     |
            ---------------------------          |
            |       < RESERVED >      | WORD     |
            ---------------------------          |>> 6 WORDS
            |         SAVED LR        | WORD     |
            ---------------------------          |
            |         SAVED CR        | WORD     |
            ---------------------------          |
            |        BACK CHAIN       | WORD     |
     SP ->  ---------------------------         --


"""
