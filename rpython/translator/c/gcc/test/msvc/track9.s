; Function compile flags: /Ogtpy
;	COMDAT _pypy_g_ll_join_strs__Signed_arrayPtr
_TEXT	SEGMENT
_pypy_g_ll_join_strs__Signed_arrayPtr PROC		; COMDAT

; 1457 : struct pypy_rpy_string0 *pypy_g_ll_join_strs__Signed_arrayPtr(long l_num_items_0, struct pypy_array0 *l_items_2) {

	sub	esp, 8
	push	ebx
	push	ebp
	push	esi

; 1458 : 	pypy_asm_gc_nocollect(open);

	call	_open
	pop	esi
	pop	ebp
$block4$40052:
	pop	ebx

; 1535 : 	goto block1_back;
; 1536 : }

	add	esp, 8
	ret	0
_pypy_g_ll_join_strs__Signed_arrayPtr ENDP
