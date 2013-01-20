	.type	PyErr_Format, @function
PyErr_Format:
.LFB67:
	.cfi_startproc
	pushq	%rbp
	.cfi_def_cfa_offset 16
	movzbl	%al, %eax
	pushq	%rbx
	.cfi_def_cfa_offset 24
	movq	%rdi, %rbx
	.cfi_offset 3, -24
	.cfi_offset 6, -16
	movq	%rsi, %rdi
	subq	$216, %rsp
	.cfi_def_cfa_offset 240
	movq	%rdx, 48(%rsp)
	leaq	0(,%rax,4), %rdx
	movl	$.L21, %eax
	movq	%rcx, 56(%rsp)
	movq	%r8, 64(%rsp)
	movq	%rsp, %rsi
	subq	%rdx, %rax
	leaq	207(%rsp), %rdx
	movq	%r9, 72(%rsp)
	jmp	*%rax
	movaps	%xmm7, -15(%rdx)
	movaps	%xmm6, -31(%rdx)
	movaps	%xmm5, -47(%rdx)
	movaps	%xmm4, -63(%rdx)
	movaps	%xmm3, -79(%rdx)
	movaps	%xmm2, -95(%rdx)
	movaps	%xmm1, -111(%rdx)
	movaps	%xmm0, -127(%rdx)
.L21:
	leaq	240(%rsp), %rax
	movl	$16, (%rsp)
	movl	$48, 4(%rsp)
	movq	%rax, 8(%rsp)
	leaq	32(%rsp), %rax
	movq	%rax, 16(%rsp)
	call	PyString_FromFormatV
	;; expected {232(%rsp) | 216(%rsp), %r12, %r13, %r14, %r15, 224(%rsp) | }
	movq	%rbx, %rdi
	movq	%rax, %rbp
	movq	%rax, %rsi
	call	PyErr_SetObject
	;; expected {232(%rsp) | 216(%rsp), %r12, %r13, %r14, %r15, 224(%rsp) | }
	movq	%rbp, %rdi
	call	Py_DecRef
	;; expected {232(%rsp) | 216(%rsp), %r12, %r13, %r14, %r15, 224(%rsp) | }
	addq	$216, %rsp
	xorl	%eax, %eax
	popq	%rbx
	popq	%rbp
	ret
	.cfi_endproc
.LFE67:
	.size	PyErr_Format, .-PyErr_Format
