_TEXT	SEGMENT
_pypy_g_foo PROC					; COMDAT

	push	ebp
	mov	ebp, esp
	and	esp, -64
	sub	esp, 12
	push	esi
	call	_pypy_g_something_else
	;; expected {4(%ebp) | %ebx, (%esp), %edi, (%ebp) | }
	pop	esi
	mov	esp, ebp
	pop	ebp
	ret	0
_pypy_g_foo ENDP
