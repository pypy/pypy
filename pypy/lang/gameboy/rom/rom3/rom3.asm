; ==========================================================================
; Noptest ROM example
; ==========================================================================

; First we includ the Gameboy Hardware Definitions
; into our assembly file, so that we get some nice
; constants and macros available.
INCLUDE "../include/gbhd.inc"

; Start a section at address $100.
SECTION "Main code section", HOME[$100]

    ; Start with a nop and a jump
    nop
    jp      main

    ; Create a ROM header (NO MBC)
    ROM_HEADER ROM_NOMBC, ROM_SIZE_32KBYTE, RAM_SIZE_0KBYTE

; --------------------------------------------------------------------------
; Main code entry point
; --------------------------------------------------------------------------
main:
    ; Nop nop nop ...
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop

; All done, so let's jump in an infinite loop. Note that this is NOT the
; correct way to end the CPU loop!
.hangup:
    jp      .hangup
