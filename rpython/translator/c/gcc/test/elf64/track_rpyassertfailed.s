	.type	pypy_g_handler_inline_call_r_v_1, @function
pypy_g_handler_inline_call_r_v_1:
.L10041:
	pushq	%r15
	movq	8(%rsi), %r15
	call	foo_bar
	;; expected {8(%rsp) | %rbx, %r12, %r13, %r14, (%rsp), %rbp | %r15}
	testq	%rax, %rax
	jne	.L10088
	movq	(%ebp), %r15
	call	RPyAssertFailed
.L10088:
	/* GCROOT %r15 */
	popq	%r15
	ret
	.size	pypy_g_handler_inline_call_r_v_1, .-pypy_g_handler_inline_call_r_v_1
