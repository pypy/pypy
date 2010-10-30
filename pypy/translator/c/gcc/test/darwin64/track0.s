_PyObject_Realloc:
LFB118:
	movq	%rbx, -32(%rsp)
LCFI86:
	movq	%rbp, -24(%rsp)
LCFI87:
	movq	%r12, -16(%rsp)
LCFI88:
	movq	%r13, -8(%rsp)
LCFI89:
	subq	$40, %rsp
LCFI90:
	movq	%rdi, %rbx
	testq	%rdi, %rdi
	je	L384
	movq	%rdi, %rbp
	andq	$-4096, %rbp
	movl	32(%rbp), %edx
	movl	_narenas(%rip), %eax
	cmpl	%eax, %edx
	jae	L360
	movq	_arenas(%rip), %rax
	mov	%edx, %edx
	movq	%rdi, %rcx
	subq	(%rax,%rdx,8), %rcx
	cmpq	$262143, %rcx
	ja	L360
	movl	36(%rbp), %ecx
	incl	%ecx
	leal	0(,%rcx,8), %r12d
	mov	%r12d, %eax
	cmpq	%rax, %rsi
	ja	L363
	leaq	0(,%rsi,4), %rdx
	sall	$4, %ecx
	leal	(%rcx,%r12), %eax
	mov	%eax, %eax
	cmpq	%rax, %rdx
	ja	L365
	movl	%esi, %r12d
L363:
	movq	%rsi, %rdi
	call	_PyObject_Malloc
	;; expected {40(%rsp) | 8(%rsp), 24(%rsp), 32(%rsp), %r14, %r15, 16(%rsp) | }
	testq	%rax, %rax
	je	L367
	mov	%r12d, %edx
	movq	%rbx, %rsi
	movq	%rax, %rdi
	call	_memcpy
	;; expected {40(%rsp) | 8(%rsp), 24(%rsp), 32(%rsp), %r14, %r15, 16(%rsp) | }
	movl	32(%rbp), %edx
	movl	_narenas(%rip), %eax
	cmpl	%eax, %edx
	jae	L369
	movq	_arenas(%rip), %rax
	mov	%edx, %edx
	movq	%rbx, %rcx
	subq	(%rax,%rdx,8), %rcx
	cmpq	$262143, %rcx
	jbe	L385
L369:
	movq	%rbx, %rdi
	call	_free
	;; expected {40(%rsp) | 8(%rsp), 24(%rsp), 32(%rsp), %r14, %r15, 16(%rsp) | }
	movq	%r13, %rbx
	jmp	L365
	.align 4,0x90
L360:
	testq	%rsi, %rsi
	jne	L386
	movl	$1, %esi
	movq	%rbx, %rdi
	call	_realloc
	;; expected {40(%rsp) | 8(%rsp), 24(%rsp), 32(%rsp), %r14, %r15, 16(%rsp) | }
	testq	%rax, %rax
	cmovne	%rax, %rbx
L365:
	movq	%rbx, %rax
	movq	8(%rsp), %rbx
	movq	16(%rsp), %rbp
	movq	24(%rsp), %r12
	movq	32(%rsp), %r13
	addq	$40, %rsp
	ret
	.align 4,0x90
L386:
	movq	%rbx, %rdi
	movq	8(%rsp), %rbx
	movq	16(%rsp), %rbp
	movq	24(%rsp), %r12
	movq	32(%rsp), %r13
	addq	$40, %rsp
	jmp	_realloc
L384:
	movq	%rsi, %rdi
	movq	8(%rsp), %rbx
	movq	16(%rsp), %rbp
	movq	24(%rsp), %r12
	movq	32(%rsp), %r13
	addq	$40, %rsp
	jmp	_PyObject_Malloc
L367:
	movq	%r13, %rbx
	jmp	L365
L385:
	movl	(%rbp), %esi
	testl	%esi, %esi
	je	L387
	movq	8(%rbp), %rax
	movq	%rax, (%rbx)
	movq	%rbx, 8(%rbp)
	testq	%rax, %rax
	je	L374
	movl	(%rbp), %eax
	decl	%eax
	movl	%eax, (%rbp)
	testl	%eax, %eax
	jne	L367
	movq	16(%rbp), %rdx
	movq	24(%rbp), %rax
	movq	%rax, 24(%rdx)
	movq	%rdx, 16(%rax)
	movq	_freepools(%rip), %rax
	movq	%rax, 16(%rbp)
	movq	%rbp, _freepools(%rip)
	movq	%r13, %rbx
	jmp	L365
L374:
	movl	(%rbp), %eax
	decl	%eax
	movl	%eax, (%rbp)
	testl	%eax, %eax
	je	L388
	movl	36(%rbp), %eax
	addl	%eax, %eax
	mov	%eax, %eax
	leaq	_usedpools(%rip), %rdx
	movq	(%rdx,%rax,8), %rax
	movq	24(%rax), %rdx
	movq	%rax, 16(%rbp)
	movq	%rdx, 24(%rbp)
	movq	%rbp, 24(%rax)
	movq	%rbp, 16(%rdx)
	movq	%r13, %rbx
	jmp	L365
L387:
	leaq	LC6(%rip), %rcx
	movl	$744, %edx
	leaq	LC7(%rip), %rsi
	leaq	___func__.207211(%rip), %rdi
	call	___assert_rtn
L388:
	leaq	LC6(%rip), %rcx
	movl	$783, %edx
	leaq	LC7(%rip), %rsi
	leaq	___func__.207211(%rip), %rdi
	call	___assert_rtn
LFE118:
