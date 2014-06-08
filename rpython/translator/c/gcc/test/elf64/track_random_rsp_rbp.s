	.type	seterror.part.1, @function
seterror.part.1:
.LFB77:
	.cfi_startproc
	pushq	%r14
	.cfi_def_cfa_offset 16
	.cfi_offset 14, -16
	pushq	%r13
	.cfi_def_cfa_offset 24
	.cfi_offset 13, -24
	pushq	%r12
	.cfi_def_cfa_offset 32
	.cfi_offset 12, -32
	pushq	%rbp
	.cfi_def_cfa_offset 40
	.cfi_offset 6, -40
	pushq	%rbx
	.cfi_def_cfa_offset 48
	.cfi_offset 3, -48
	subq	$512, %rsp
	.cfi_def_cfa_offset 560
	testq	%r8, %r8
	je	.L30
.L11:
	movq	PyPyExc_TypeError@GOTPCREL(%rip), %rax
	movq	%r8, %rsi
	movq	(%rax), %rdi
	call	PyPyErr_SetString@PLT
	;; expected {552(%rsp) | 512(%rsp), 528(%rsp), 536(%rsp), 544(%rsp), %r15, 520(%rsp) | }
	addq	$512, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 48
	popq	%rbx
	.cfi_def_cfa_offset 40
	popq	%rbp
	.cfi_def_cfa_offset 32
	popq	%r12
	.cfi_def_cfa_offset 24
	popq	%r13
	.cfi_def_cfa_offset 16
	popq	%r14
	.cfi_def_cfa_offset 8
	ret
	.p2align 4,,10
	.p2align 3
.L30:
	.cfi_restore_state
	testq	%rcx, %rcx
	movq	%rsi, %r12
	movl	%edi, %r14d
	movq	%rdx, %r13
	movq	%rsp, %rbp
	movl	$512, %esi
	movq	%rsp, %rbx
	je	.L13
	leaq	.LC6(%rip), %rdx
	movl	$512, %esi
	movq	%rsp, %rdi
	xorl	%eax, %eax
	movq	%rsp, %rbx
	call	PyPyOS_snprintf@PLT
	;; expected {552(%rsp) | 512(%rsp), 528(%rsp), 536(%rsp), 544(%rsp), %r15, 520(%rsp) | }
.L14:
	movl	(%rbx), %eax
	addq	$4, %rbx
	leal	-16843009(%rax), %esi
	notl	%eax
	andl	%eax, %esi
	andl	$-2139062144, %esi
	je	.L14
	movl	%esi, %eax
	shrl	$16, %eax
	testl	$32896, %esi
	cmove	%eax, %esi
	leaq	2(%rbx), %rax
	cmove	%rax, %rbx
	addb	%sil, %sil
	movq	%rbp, %rsi
	sbbq	$3, %rbx
	subq	%rbx, %rsi
	addq	$512, %rsi
.L13:
	testl	%r14d, %r14d
	je	.L16
	leaq	.LC7(%rip), %rdx
	movq	%rbx, %rdi
	movl	%r14d, %ecx
	xorl	%eax, %eax
	call	PyPyOS_snprintf@PLT
	;; expected {552(%rsp) | 512(%rsp), 528(%rsp), 536(%rsp), 544(%rsp), %r15, 520(%rsp) | }
	movq	%rbx, %rdi
	call	strlen@PLT
	;; expected {552(%rsp) | 512(%rsp), 528(%rsp), 536(%rsp), 544(%rsp), %r15, 520(%rsp) | }
	addq	%rax, %rbx
	movl	0(%r13), %eax
	testl	%eax, %eax
	jle	.L18
	movq	%rbx, %rdx
	subq	%rbp, %rdx
	cmpl	$219, %edx
	jg	.L18
	addq	$4, %r13
	xorl	%r14d, %r14d
	.p2align 4,,10
	.p2align 3
.L21:
	movq	%rbp, %rsi
	leal	-1(%rax), %ecx
	leaq	.LC8(%rip), %rdx
	subq	%rbx, %rsi
	movq	%rbx, %rdi
	xorl	%eax, %eax
	addq	$512, %rsi
	addl	$1, %r14d
	call	PyPyOS_snprintf@PLT
	;; expected {552(%rsp) | 512(%rsp), 528(%rsp), 536(%rsp), 544(%rsp), %r15, 520(%rsp) | }
	movq	%rbx, %rdi
	call	strlen@PLT
	;; expected {552(%rsp) | 512(%rsp), 528(%rsp), 536(%rsp), 544(%rsp), %r15, 520(%rsp) | }
	addq	%rax, %rbx
	movl	0(%r13), %eax
	testl	%eax, %eax
	jle	.L18
	cmpl	$32, %r14d
	je	.L18
	movq	%rbx, %rdx
	addq	$4, %r13
	subq	%rbp, %rdx
	cmpl	$219, %edx
	jle	.L21
	jmp	.L18
	.p2align 4,,10
	.p2align 3
.L16:
	leaq	.LC9(%rip), %rdx
	movq	%rbx, %rdi
	xorl	%eax, %eax
	call	PyPyOS_snprintf@PLT
	;; expected {552(%rsp) | 512(%rsp), 528(%rsp), 536(%rsp), 544(%rsp), %r15, 520(%rsp) | }
	movq	%rbx, %rdi
	call	strlen@PLT
	;; expected {552(%rsp) | 512(%rsp), 528(%rsp), 536(%rsp), 544(%rsp), %r15, 520(%rsp) | }
	addq	%rax, %rbx
.L18:
	movq	%rbp, %rsi
	leaq	.LC10(%rip), %rdx
	movq	%r12, %rcx
	subq	%rbx, %rsi
	movq	%rbx, %rdi
	xorl	%eax, %eax
	addq	$512, %rsi
	call	PyPyOS_snprintf@PLT
	;; expected {552(%rsp) | 512(%rsp), 528(%rsp), 536(%rsp), 544(%rsp), %r15, 520(%rsp) | }
	movq	%rbp, %r8
	jmp	.L11
	.cfi_endproc
.LFE77:
	.size	seterror.part.1, .-seterror.part.1
