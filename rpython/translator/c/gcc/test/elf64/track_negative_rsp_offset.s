	.type some_function, @function
some_function:
	;; Test using a negative offset from %rsp (gcc sometimes does this)
	movq %rbx, -8(%rsp)
	subq $8, %rsp

	movq %rdi, %rbx

	call some_other_function
	;; expected {8(%rsp) | (%rsp), %r12, %r13, %r14, %r15, %rbp | %rbx}
	/* GCROOT %rbx */

	movq %rbx, %rax
	;; Same as where %rbx was saved above
	movq (%rsp), %rbx
	ret
	.size some_function, .-some_function
