; Function compile flags: /Odtp
_TEXT	SEGMENT
_pypy_g_frameworkgc_setup PROC

; 46   : void pypy_g_frameworkgc_setup(void) {

	push	ebp
	mov	ebp, esp
$block0$37400:

; 47   : 
; 48   :     block0:
; 49   : 	pypy_g_SemiSpaceGC_setup((&pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC));

	push	OFFSET _pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC
	call	_pypy_g_SemiSpaceGC_setup
      ;; expected {4(%ebp) | %ebx, %esi, %edi, (%ebp) | }
	add	esp, 4
$block1$37401:

; 50   : 	goto block1;
; 51   : 
; 52   :     block1:
; 53   : 	RPY_DEBUG_RETURN();
; 54   : 	return /* nothing */;
; 55   : }

	pop	ebp
	ret	0
_pypy_g_frameworkgc_setup ENDP
_TEXT	ENDS
