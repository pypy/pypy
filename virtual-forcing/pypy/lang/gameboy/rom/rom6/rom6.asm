; ==========================================================================
; ROM6
; ==========================================================================

; First we includ the Gameboy Hardware Definitions
; into our assembly file, so that we get some nice
; constants and macros available.
INCLUDE "../include/gbhd.inc"

; Start a section at address $0.
SECTION "Main code section", HOME[$0]

RST_00:	jp	main
	DS	5
RST_08:	jp	main
	DS	5
RST_10:	jp	main
	DS	5
RST_18:	jp	main
	DS	5
RST_20:	jp	main
	DS	5
RST_28:	jp	main
	DS	5
RST_30:	jp	main
	DS	5
RST_38:	jp	main
	DS	5
	jp	main ;irq_VBlank
	DS	5
	jp	main ;irq_LCDC
	DS	5
	jp	main ;irq_Timer
	DS	5
	jp	main ;irq_Serial
	DS	5
	jp	main ;irq_HiLo
	DS	5

	DS	$100-$68
	
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
	ld  hl, topOfStack
	ld  sp, hl

    CART_MBC1_SELECT_MEMORY_MODE CART_MBC1_MODE_4MBIT

    CART_MBC1_SELECT_BANK_5BIT 1    ; selects ROM bank 1
    CART_MBC1_SELECT_BANK_2BIT 0    ; selects RAM bank 0

    CART_MBC1_ENABLE_RAM            ; enable RAM
    
    ; Write cartridge RAM full of $ff
    ld  hl, _CART_RAM
    ld  bc, $20 ;$2000
    ld  a, $ff
    call    memSet

    CART_MBC1_SELECT_BANK_2BIT 1    ; selects RAM bank 1
    
    ; Write cartridge RAM full of $22
    ld  hl, _CART_RAM
    ld  bc, $20 ;$2000
    ld  a, $22
    call    memSet
    
    CART_MBC1_SELECT_BANK_2BIT 0    ; selects RAM bank 0
    
    ; Compare the first byte of the RAM
    ld  a, $ff
    ld  hl, _CART_RAM
    cp  [hl]
    jr  NZ, .not_equal  ; content was not ok, then jump
    
    xor a

.not_equal:

    ; Stop CPU
    db $76  ; halt (instruction coded as data because RGBASM adds a nop after a halt)
    db $76  ; halt

    ; Breakpoint
    db $dd  ; dbg
    
; Just do the hangup here
.hangup:
    jp      .hangup


; --------------------------------------------------------------------------
; memSet - Set a memory region
;
; input:
;   a - value to write
;   hl - memory address
;   bc - bytecount
; --------------------------------------------------------------------------
memSet:
	inc	b
	inc	c
	jr	.skip
.loop	ld	[hl+],a
.skip	dec	c
	jr	nz,.loop
	dec	b
	jr	nz,.loop
	ret

SECTION	"Stack",BSS

stack:
	DS	$200
topOfStack: