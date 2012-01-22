	.type	main1, @function
main1:
	pushl	%ebx
	call	pypy_f
	;; expected {4(%esp) | (%esp), %esi, %edi, %ebp | %ebx}
	je	.L1
	call	RPyAssertFailed
	;; the following call is not reachable:	it should be ignored
	call	pypy_malloc_something
.L1:
	/* GCROOT %ebx */
	popl	%ebx
	ret
	.size	main1, .-main1
