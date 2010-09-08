	.type	foobar, @function
foobar:
	pushq %rbp
	movq %rsp, %rbp
	call some_function
	;; expected {8(%rbp) | %rbx, %r12, %r13, %r14, %r15, (%rbp) | }
	movl $const1, %edx
	movl $const2, %r10d
	xorl %r10d, %r11d
	/* GCROOT %rdx */
	/* GCROOT %r10 */
	/* GCROOT %r11 */
	leave
	ret
	.size	foobar, .-foobar
