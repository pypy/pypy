; ==========================================================================
; ROM5
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
    
    ; Test 1: The simple loop
    xor     a
.loop1:
    dec     a
    jp      NZ, .loop1
    
    db $dd  ; dbg
    
    ; Test 2: The loop with relative conditional jump
    xor     a
.loop2:
    add     a, 1
    jr      NC, .loop2
    
    db $dd  ; dbg

    ; Test 3: The loop again, but different somehow
    xor     a
.loop3:
    inc     a
    jp      NC, .loop3

    db $dd  ; dbg
    
    ; Stop CPU
    db $76  ; halt (instruction coded as data because RGBASM adds a nop after a halt)
    db $76  ; halt

    ; Put $ff in a to indicate that stop did not work
    ld      a, $ff

    ; Breakpoint
    db $dd  ; dbg
    
; Just do the hangup here
.hangup:
    jp      .hangup
