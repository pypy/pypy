	.type	pypy_g_do_call_1, @function
pypy_g_do_call_1:
	pushq	%rbx
	movq	%rdi, %rbx
	call	number1
	;; expected {8(%rsp) | (%rsp), %r12, %r13, %r14, %r15, %rbp | %rbx}
	testq	%rax, %rax
	je .L1
	call	RPyAssertFailed
.L1:
	/* GCROOT %rbx */
	popq	%rbx
	ret
	.size	pypy_g_do_call_1, .-pypy_g_do_call_1
