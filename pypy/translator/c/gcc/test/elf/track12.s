	.type	pypy_f, @function
pypy_f:
	pushl   4(%esp)
	call    pypy_other
	;; expected {4(%esp) | %ebx, %esi, %edi, %ebp | (%esp)}
	popl    %eax
	/* GCROOT %eax */
	ret
	.size	pypy_f, .-pypy_f
