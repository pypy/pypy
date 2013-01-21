	.type	pypy_g_do_call_1, @function
pypy_g_do_call_1:
	pushq	%rbx
	pushq	%r12
	movq	%rdi, %rbx
	movq	%rsi, %r12
	call	number1
	;; expected {16(%rsp) | 8(%rsp), (%rsp), %r13, %r14, %r15, %rbp | %r12}
	testq	%rbx, %rbx
	movq	%r12, %rbx
	je .L1
	movq	(%rax), %rbx
.L1:
	/* GCROOT %rbx */
	popq	%r12
	popq	%rbx
	ret
	.size	pypy_g_do_call_1, .-pypy_g_do_call_1
