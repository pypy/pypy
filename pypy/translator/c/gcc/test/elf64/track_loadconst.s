	.type	pypy_g_handler_inline_call_r_v_1, @function
pypy_g_handler_inline_call_r_v_1:
	pushq	%rbp
	call	foo_bar
	;; expected {8(%rsp) | %rbx, %r12, %r13, %r14, %r15, (%rsp) | }
	movl	$pypy_g_some_prebuilt_gc_object, %ebp
	call	bar_baz
	;; expected {8(%rsp) | %rbx, %r12, %r13, %r14, %r15, (%rsp) | %rbp}
	/* GCROOT %rbp */
	popq	%rbp
	ret
	.size	pypy_g_handler_inline_call_r_v_1, .-pypy_g_handler_inline_call_r_v_1
