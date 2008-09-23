; ==========================================================================
; ROM4
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
    ; Disable interupts
    di
    
    ; Turn off screen, please know that this is actually not the correct way
    ; to turn off the screen, since we normally would have to wait for vertical
    ; blank. But for now, it's ok.
    ld      hl, rLCDC
    res     7, [hl]
    
    ; Stop CPU
    db $76  ; halt (instruction coded as data because RGBASM adds a nop after a halt)
    db $76  ; halt

    ; Put $ff in a to indicate that stop did not work
    ld      a, $ff

; Just do the hangup here    
.hangup:
    jp      .hangup
