; ==========================================================================
; ROM9
; ==========================================================================

; First we includ the Gameboy Hardware Definitions
; into our assembly file, so that we get some nice
; constants and macros available.
INCLUDE "../include/gbhd.inc"

; Also include a file that can generate a set of characters in the IBM PC1
; font face.
INCLUDE "../include/ibmpc1.inc"

; SECTION ------------------------------------------------------------------

; Start a section at address $0.
SECTION "Main code section", HOME[$0]

RST_00: jp  main
  DS  5
RST_08: jp  main
  DS  5
RST_10: jp  main
  DS  5
RST_18: jp  main
  DS  5
RST_20: jp  main
  DS  5
RST_28: jp  main
  DS  5
RST_30: jp  main
  DS  5
RST_38: jp  main
  DS  5
  jp  main ;irq_VBlank
  DS  5
  jp  main ;irq_LCDC
  DS  5
  jp  main ;irq_Timer
  DS  5
  jp  main ;irq_Serial
  DS  5
  jp  main ;irq_HiLo
  DS  5

  DS  $100-$68
  
    ; Start with a nop and a jump
    nop
    jp      main

    ; Create a ROM header (MBC1, 64kB ROM, 32kB RAM)
    ROM_HEADER ROM_MBC1_RAM, ROM_SIZE_64KBYTE, RAM_SIZE_32KBYTE

; --------------------------------------------------------------------------
; Main code entry point
; --------------------------------------------------------------------------
main:
    ; Disable interupts
    di

    ; Initialize stack
    ld    sp, topOfStack

    ; Stop the LCD
    call  stopLCD

    ; Setup cart controller
    CART_MBC1_SELECT_MEMORY_MODE CART_MBC1_MODE_4MBIT
    CART_MBC1_SELECT_BANK_5BIT 1    ; selects ROM bank 1
    CART_MBC1_SELECT_BANK_2BIT 0    ; selects RAM bank 0
    CART_MBC1_ENABLE_RAM            ; enable RAM
    
    ; Set the palette to shades of grey
    ld    a, $e4
    ld    [rBGP], a             ; Setup the default background palette
    
    ; We set the scroll registers to 0 so that we can
    ; view the upper left corner of the background.
    ld    a, 0
    ld    [rSCX], a
    ld    [rSCY], a
    
    ; Copy the 256 character font data to the VRAM (in order)
    ld    hl, font
    ld    de, _VRAM
    ld    bc, 8 * 256           ; length (8 bytes per tile) x (256 tiles)
    call  memCopyMono           ; copy tile data to memory    
    
    ; Clear tile map memory with 'spaces' ($20)
    ld    a, $20
    ld    hl, _SCRN0
    ld    bc, SCRN_VX_B * SCRN_VY_B
    call  memSet

    ; Setup Sprite 0
    ld    hl, _OAMRAM
    ld    a, 70
    ld    [hl+], a
    xor   a
    ld    [hl+], a
    ld    a, 1
    ld    [hl+], a
    xor   a
    ld    [hl+], a

    ; Turn on the screen
    call startLCD
    
    ; Write the Hello world string
    ld    hl, helloWorld
    ld    de, _SCRN0 + 4 + (SCRN_VY_B * 7)
    ld    b, 12
.loop12:
    call  waitVBE
    ld    a, [hl+]
    ld    [de], a
    inc   de
    dec   b
    jr    nz, .loop12
    
    
; Just loop
.hangup:
    ld    hl, _OAMRAM + 1
    ld    a, [hl]
    inc   a
    ld    [hl], a
    call  waitVBE
    jp    .hangup
    
    
; --------------------------------------------------------------------------
; memSet - Set a memory region
;
; input:
;   a - value to write
;   hl - memory address
;   bc - bytecount
; --------------------------------------------------------------------------
memSet:
  inc b
  inc c
  jr  .skip
.loop ld  [hl+], a
.skip dec c
  jr  nz, .loop
  dec b
  jr  nz, .loop
  ret


; --------------------------------------------------------------------------
; memCopy - Copy memory from ROM/RAM to RAM

; input:
;   hl - source address
;   de - destination address
;   bc - bytecount of source
; --------------------------------------------------------------------------
memCopy:
  inc b
  inc c
  jr  .skip
.loop ld  a, [hl+]
  ld  [de], a
  inc de
.skip dec c
  jr  nz, .loop
  dec b
  jr  nz, .loop
  ret


; --------------------------------------------------------------------------
; memCopyMono - "Copy" a monochrome font from ROM to RAM (it basically
;               writes every byte of the source twice to the destination, so
;               the destination space is double of the source space)
; input:
;   hl - source address
;   de - destination address
;   bc - bytecount of source
; --------------------------------------------------------------------------
memCopyMono:
  inc b
  inc c
  jr  .skip
.loop ld  a, [hl+]
  ld  [de], a
  inc de
  ld  [de], a
  inc de
.skip dec c
  jr  nz, .loop
  dec b
  jr  nz, .loop
  ret


; --------------------------------------------------------------------------
; waitVBE - Wait for Vertical Blank
; --------------------------------------------------------------------------
waitVBE:
; Loop until we are in VBlank
        push    af
.wait:
        ld      a, [rLY]
        cp      145             ; Is display on scan line 145 yet?
        jr      nz, .wait       ; no, keep waiting
        pop     af
        ret

; --------------------------------------------------------------------------
; stopLCD - Stops the LCD (turn off screen)
; --------------------------------------------------------------------------
stopLCD:
        ld      a, [rLCDC]
        rlca                    ; Put the high bit of LCDC into the Carry flag
        ret     nc              ; Screen is off already. Exit.
; Loop until we are in VBlank
.wait:
        ld      a, [rLY]
        cp      145             ; Is display on scan line 145 yet?
        jr      nz, .wait       ; no, keep waiting
; Turn off the LCD
        ld      a, [rLCDC]
        res     7, a            ; Reset bit 7 of LCDC
        ld      [rLCDC], a
; Return
        ret


; --------------------------------------------------------------------------
; startLCD - Start the LCD (turn on screen)
; --------------------------------------------------------------------------
startLCD:
        ld      a, LCDCF_ON | LCDCF_BG8000 | LCDCF_BG9800 | LCDCF_BGON | LCDCF_OBJ8 | LCDCF_OBJON
        ld      [rLCDC], a      ; Turn screen on
        ret


; Generate a full 256 character font set.
font:
    chr_IBMPC1  1,8

helloWorld:
    db  "Hello world!"

; SECTION ------------------------------------------------------------------

SECTION "Stack",BSS

stack:
  DS  $200
topOfStack: