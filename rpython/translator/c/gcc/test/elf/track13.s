	.type	pypy_f, @function
pypy_f:
	call    pypy_other
	;; expected {(%esp) | %ebx, %esi, %edi, %ebp | 8(%esp)}
	pushl   8(%esp)
	popl    %eax
	/* GCROOT %eax */
	ret
	.size	pypy_f, .-pypy_f
