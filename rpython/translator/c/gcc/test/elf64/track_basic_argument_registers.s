	.type	foobar, @function
foobar:
.LFB0:
	.cfi_startproc
	pushq	%rbp
	.cfi_def_cfa_offset 16
	movq	%rsp, %rbp
	.cfi_offset 6, -16
	.cfi_def_cfa_register 6
	subq	$48, %rsp
	movq	%rdi, -8(%rbp)
	movq	%rsi, -16(%rbp)
	movq	%rdx, -24(%rbp)
	movq	%rcx, -32(%rbp)
	movq	%r8, -40(%rbp)
	movq	%r9, -48(%rbp)
	movl	$0, %eax
	call	some_function
	;; expected {8(%rbp) | %rbx, %r12, %r13, %r14, %r15, (%rbp) | -8(%rbp), -16(%rbp), -24(%rbp), -32(%rbp), -40(%rbp), -48(%rbp)}
	/* GCROOT -8(%rbp) */
	/* GCROOT -16(%rbp) */
	/* GCROOT -24(%rbp) */
	/* GCROOT -32(%rbp) */
	/* GCROOT -40(%rbp) */
	/* GCROOT -48(%rbp) */
	movq	-24(%rbp), %rax
	leave
	; try out a "rep ret" instead of just a "ret", for bad reasons
	rep ret
	.cfi_endproc
.LFE0:
	.size	foobar, .-foobar
