	.type	pypy_g_do_call_1, @function
pypy_g_do_call_1:
	pushq	%rbx
	pushq	%r12
	movq	%rdi, %rbx
	movq	%rsi, %r12
	call	number1
	;; expected {16(%rsp) | 8(%rsp), (%rsp), %r13, %r14, %r15, %rbp | %r12}
	testq	%rbx, %rbx	; here rbx is an integer, not a gc ref
	je .L1			; if rbx==0, jump to L1, where rbx==NULLGCREF
	movq	(%rax), %rbx	; else load a gc ref
.L1:
	/* GCROOT %rbx */
	/* GCROOT %r12 */
	popq	%r12
	popq	%rbx
	ret
	.size	pypy_g_do_call_1, .-pypy_g_do_call_1
