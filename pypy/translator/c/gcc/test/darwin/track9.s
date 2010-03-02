_pypy_g_foo:
L1506:
	pushl	%ebp
	pushl	%edi
	pushl	%esi
	pushl	%ebx
	call	L103
"L00000000006$pb":
L103:
	popl	%ebx
	call	_open
	/* GC_NOCOLLECT open */
	popl	%ebx
	popl	%esi
	popl	%edi
	popl	%ebp
	ret
	.align 4,0x90
