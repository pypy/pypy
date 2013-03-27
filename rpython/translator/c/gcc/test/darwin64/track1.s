_pypy_g_PyObject_RichCompare:
LFB302:
	movq	%rbx, -48(%rsp)
LCFI297:
	movq	%rbp, -40(%rsp)
LCFI298:
	movq	%r12, -32(%rsp)
LCFI299:
	movq	%r13, -24(%rsp)
LCFI300:
	movq	%r14, -16(%rsp)
LCFI301:
	movq	%r15, -8(%rsp)
LCFI302:
	subq	$88, %rsp
LCFI303:
	movq	%rdi, %rbx
	movq	%rsi, %rbp
L970:
	cmpl	$5, %edx
	jbe	L1056
L971:
	movq	_pypy_g_pypy_rpython_memory_gc_minimark_MiniMarkGC@GOTPCREL(%rip), %rdi
	movq	16(%rdi), %rdx
	leaq	16(%rdx), %rax
	movq	%rax, 16(%rdi)
	cmpq	24(%rdi), %rax
	ja	L1034
	movq	%rdx, %rbx
	movq	_pypy_g_ExcData@GOTPCREL(%rip), %r11
L1036:
	movq	$61224, (%rbx)
	movq	$0, 8(%rdx)
L1037:
	movq	%r11, (%rsp)
	call	_pypy_g_PyErr_BadInternalCall
	;; expected {88(%rsp) | 40(%rsp), 56(%rsp), 64(%rsp), 72(%rsp), 80(%rsp), 48(%rsp) | %rbx}
	movq	___gcmapend@GOTPCREL(%rip), %rax
	/* GCROOT %rbx */
	movq	(%rsp), %r11
	movq	(%r11), %rbp
	testq	%rbp, %rbp
	je	L1057
L1038:
	movq	8(%r11), %r12
	movq	_pypydtcount@GOTPCREL(%rip), %r10
	movl	(%r10), %eax
	movq	_pypy_debug_tracebacks@GOTPCREL(%rip), %r9
	movslq	%eax,%rdx
	salq	$4, %rdx
	leaq	_loc.235055(%rip), %rcx
	movq	%rcx, (%rdx,%r9)
	movq	%rbp, 8(%rdx,%r9)
	incl	%eax
	andl	$127, %eax
	movl	%eax, (%r10)
	movq	_pypy_g_typeinfo@GOTPCREL(%rip), %r8
	leaq	59688(%r8), %rax
	cmpq	%rax, %rbp
	je	L1040
	leaq	59544(%r8), %rax
	cmpq	%rax, %rbp
	je	L1040
L1042:
	movq	$0, 8(%r11)
	movq	$0, (%r11)
	/* keepalive %r12 */
	/* keepalive %rbx */
L1043:
L1044:
	/* GC_NOCOLLECT pypy_g_ll_issubclass */
L1046:
L1047:
	/* keepalive %rbx */
	cmpq	$0, 8(%rbx)
	jle	L1048
L1049:
	/* keepalive %rbx */
L1050:
	leaq	59688(%r8), %rcx
	movq	%rcx, (%r11)
	movq	_pypy_g_exceptions_AssertionError_6@GOTPCREL(%rip), %rax
	movq	%rax, 8(%r11)
	movl	(%r10), %edx
	movslq	%edx,%rax
	salq	$4, %rax
	movq	$0, (%rax,%r9)
	movq	%rcx, 8(%rax,%r9)
	incl	%edx
	andl	$127, %edx
	/* GC_NOCOLLECT pypy_g_RPyRaiseException */
	movslq	%edx,%rax
	salq	$4, %rax
	leaq	_loc.235061(%rip), %rbx
	movq	%rbx, (%rax,%r9)
	movq	$0, 8(%rax,%r9)
	incl	%edx
	andl	$127, %edx
	movl	%edx, (%r10)
	xorl	%eax, %eax
	.align 4,0x90
L981:
	movq	40(%rsp), %rbx
	movq	48(%rsp), %rbp
	movq	56(%rsp), %r12
	movq	64(%rsp), %r13
	movq	72(%rsp), %r14
	movq	80(%rsp), %r15
	addq	$88, %rsp
	ret
	.align 4,0x90
L1056:
	mov	%edx, %eax
	leaq	L978(%rip), %rdx
	movslq	(%rdx,%rax,4),%rax
	addq	%rdx, %rax
	jmp	*%rax
	.align 2,0x90
L978:
	.long	L972-L978
	.long	L973-L978
	.long	L974-L978
	.long	L975-L978
	.long	L976-L978
	.long	L977-L978
L972:
	/* keepalive %rdi */
	/* keepalive %rsi */
	call	_pypy_g___mm_lt_0_perform_call
	;; expected {88(%rsp) | 40(%rsp), 56(%rsp), 64(%rsp), 72(%rsp), 80(%rsp), 48(%rsp) | %rbx, %rbp}
	movq	___gcmapend@GOTPCREL(%rip), %rdx
	movq	%rbx, %r15
	/* GCROOT %r15 */
	movq	%rbp, %r14
	/* GCROOT %r14 */
	movq	%rbx, %r12
	/* GCROOT %r12 */
	/* GCROOT %rbp */
	movq	_pypy_g_ExcData@GOTPCREL(%rip), %r11
	movq	(%r11), %rbx
	testq	%rbx, %rbx
	je	L981
L979:
	movq	8(%r11), %r13
	movq	_pypydtcount@GOTPCREL(%rip), %r10
	movl	(%r10), %eax
	movq	_pypy_debug_tracebacks@GOTPCREL(%rip), %r9
	movslq	%eax,%rdx
	salq	$4, %rdx
	leaq	_loc.234970(%rip), %rcx
	movq	%rcx, (%rdx,%r9)
	movq	%rbx, 8(%rdx,%r9)
	incl	%eax
	andl	$127, %eax
	movl	%eax, (%r10)
	movq	_pypy_g_typeinfo@GOTPCREL(%rip), %r8
	leaq	59688(%r8), %rax
	cmpq	%rax, %rbx
	je	L982
	leaq	59544(%r8), %rax
	cmpq	%rax, %rbx
	je	L982
L984:
	movq	$0, 8(%r11)
	movq	$0, (%r11)
	/* keepalive %r13 */
	/* keepalive %r15 */
	/* keepalive %r14 */
	/* keepalive %r12 */
	/* keepalive %rbp */
L985:
	movq	1712(%r8), %rcx
	movq	(%rbx), %rdx
	subq	%rcx, %rdx
	movq	1720(%r8), %rax
L986:
	/* GC_NOCOLLECT pypy_g_ll_issubclass */
	subq	%rcx, %rax
	cmpq	%rax, %rdx
	jae	L1058
L987:
	/* keepalive %r12 */
	/* keepalive %rbp */
	movq	%rbp, %rsi
	movq	%r12, %rdi
	movq	40(%rsp), %rbx
	movq	48(%rsp), %rbp
	movq	56(%rsp), %r12
	movq	64(%rsp), %r13
	movq	72(%rsp), %r14
	movq	80(%rsp), %r15
	addq	$88, %rsp
	jmp	_pypy_g_comparison_lt_impl
L973:
	/* keepalive %rdi */
	/* keepalive %rsi */
	call	_pypy_g___mm_le_0_perform_call
	;; expected {88(%rsp) | 40(%rsp), 56(%rsp), 64(%rsp), 72(%rsp), 80(%rsp), 48(%rsp) | %rbx, %rbp}
	movq	___gcmapend@GOTPCREL(%rip), %rdx
	movq	%rbx, %r15
	/* GCROOT %r15 */
	movq	%rbp, %r14
	/* GCROOT %r14 */
	movq	%rbx, %r12
	/* GCROOT %r12 */
	/* GCROOT %rbp */
	movq	_pypy_g_ExcData@GOTPCREL(%rip), %r11
	movq	(%r11), %rbx
	testq	%rbx, %rbx
	je	L981
L989:
	movq	8(%r11), %r13
	movq	_pypydtcount@GOTPCREL(%rip), %r10
	movl	(%r10), %eax
	movq	_pypy_debug_tracebacks@GOTPCREL(%rip), %r9
	movslq	%eax,%rdx
	salq	$4, %rdx
	leaq	_loc.234982(%rip), %rcx
	movq	%rcx, (%rdx,%r9)
	movq	%rbx, 8(%rdx,%r9)
	incl	%eax
	andl	$127, %eax
	movl	%eax, (%r10)
	movq	_pypy_g_typeinfo@GOTPCREL(%rip), %r8
	leaq	59688(%r8), %rax
	cmpq	%rax, %rbx
	je	L991
	leaq	59544(%r8), %rax
	cmpq	%rax, %rbx
	je	L991
L993:
	movq	$0, 8(%r11)
	movq	$0, (%r11)
	/* keepalive %r13 */
	/* keepalive %r15 */
	/* keepalive %r14 */
	/* keepalive %r12 */
	/* keepalive %rbp */
L994:
	movq	1712(%r8), %rcx
	movq	(%rbx), %rdx
	subq	%rcx, %rdx
	movq	1720(%r8), %rax
L995:
	/* GC_NOCOLLECT pypy_g_ll_issubclass */
	subq	%rcx, %rax
	cmpq	%rax, %rdx
	jae	L1059
L996:
	/* keepalive %r12 */
	/* keepalive %rbp */
	movq	%rbp, %rsi
	movq	%r12, %rdi
	movq	40(%rsp), %rbx
	movq	48(%rsp), %rbp
	movq	56(%rsp), %r12
	movq	64(%rsp), %r13
	movq	72(%rsp), %r14
	movq	80(%rsp), %r15
	addq	$88, %rsp
	jmp	_pypy_g_comparison_le_impl
L974:
	/* keepalive %rdi */
	/* keepalive %rsi */
	call	_pypy_g___mm_eq_0_perform_call
	;; expected {88(%rsp) | 40(%rsp), 56(%rsp), 64(%rsp), 72(%rsp), 80(%rsp), 48(%rsp) | %rbx, %rbp}
	movq	___gcmapend@GOTPCREL(%rip), %rdx
	movq	%rbx, %r15
	/* GCROOT %r15 */
	movq	%rbp, %r14
	/* GCROOT %r14 */
	movq	%rbx, %r12
	/* GCROOT %r12 */
	/* GCROOT %rbp */
	movq	_pypy_g_ExcData@GOTPCREL(%rip), %r11
	movq	(%r11), %rbx
	testq	%rbx, %rbx
	je	L981
L998:
	movq	8(%r11), %r13
	movq	_pypydtcount@GOTPCREL(%rip), %r10
	movl	(%r10), %eax
	movq	_pypy_debug_tracebacks@GOTPCREL(%rip), %r9
	movslq	%eax,%rdx
	salq	$4, %rdx
	leaq	_loc.234994(%rip), %rcx
	movq	%rcx, (%rdx,%r9)
	movq	%rbx, 8(%rdx,%r9)
	incl	%eax
	andl	$127, %eax
	movl	%eax, (%r10)
	movq	_pypy_g_typeinfo@GOTPCREL(%rip), %r8
	leaq	59688(%r8), %rax
	cmpq	%rax, %rbx
	je	L1000
	leaq	59544(%r8), %rax
	cmpq	%rax, %rbx
	je	L1000
L1002:
	movq	$0, 8(%r11)
	movq	$0, (%r11)
	/* keepalive %r13 */
	/* keepalive %r15 */
	/* keepalive %r14 */
	/* keepalive %rbp */
	/* keepalive %r12 */
L1003:
	movq	1712(%r8), %rcx
	movq	(%rbx), %rdx
	subq	%rcx, %rdx
	movq	1720(%r8), %rax
L1004:
	/* GC_NOCOLLECT pypy_g_ll_issubclass */
	subq	%rcx, %rax
	cmpq	%rax, %rdx
	jae	L1060
L1005:
	/* keepalive %r12 */
	/* keepalive %rbp */
	movq	%rbp, %rsi
	movq	%r12, %rdi
	movq	40(%rsp), %rbx
	movq	48(%rsp), %rbp
	movq	56(%rsp), %r12
	movq	64(%rsp), %r13
	movq	72(%rsp), %r14
	movq	80(%rsp), %r15
	addq	$88, %rsp
	jmp	_pypy_g_comparison_eq_impl
L975:
	/* keepalive %rdi */
	/* keepalive %rsi */
	call	_pypy_g___mm_ne_0_perform_call
	;; expected {88(%rsp) | 40(%rsp), 56(%rsp), 64(%rsp), 72(%rsp), 80(%rsp), 48(%rsp) | %rbx, %rbp}
	movq	___gcmapend@GOTPCREL(%rip), %rdx
	movq	%rbx, %r15
	/* GCROOT %r15 */
	movq	%rbp, %r14
	/* GCROOT %r14 */
	movq	%rbx, %r12
	/* GCROOT %r12 */
	/* GCROOT %rbp */
	movq	_pypy_g_ExcData@GOTPCREL(%rip), %r11
	movq	(%r11), %rbx
	testq	%rbx, %rbx
	je	L981
L1007:
	movq	8(%r11), %r13
	movq	_pypydtcount@GOTPCREL(%rip), %r10
	movl	(%r10), %eax
	movq	_pypy_debug_tracebacks@GOTPCREL(%rip), %r9
	movslq	%eax,%rdx
	salq	$4, %rdx
	leaq	_loc.235006(%rip), %rcx
	movq	%rcx, (%rdx,%r9)
	movq	%rbx, 8(%rdx,%r9)
	incl	%eax
	andl	$127, %eax
	movl	%eax, (%r10)
	movq	_pypy_g_typeinfo@GOTPCREL(%rip), %r8
	leaq	59688(%r8), %rax
	cmpq	%rax, %rbx
	je	L1009
	leaq	59544(%r8), %rax
	cmpq	%rax, %rbx
	je	L1009
L1011:
	movq	$0, 8(%r11)
	movq	$0, (%r11)
	/* keepalive %r13 */
	/* keepalive %r15 */
	/* keepalive %r14 */
	/* keepalive %r12 */
	/* keepalive %rbp */
L1012:
	movq	1712(%r8), %rcx
	movq	(%rbx), %rdx
	subq	%rcx, %rdx
	movq	1720(%r8), %rax
L1013:
	/* GC_NOCOLLECT pypy_g_ll_issubclass */
	subq	%rcx, %rax
	cmpq	%rax, %rdx
	jae	L1061
L1014:
	/* keepalive %r12 */
	/* keepalive %rbp */
	movq	%rbp, %rsi
	movq	%r12, %rdi
	movq	40(%rsp), %rbx
	movq	48(%rsp), %rbp
	movq	56(%rsp), %r12
	movq	64(%rsp), %r13
	movq	72(%rsp), %r14
	movq	80(%rsp), %r15
	addq	$88, %rsp
	jmp	_pypy_g_comparison_ne_impl
L976:
	/* keepalive %rdi */
	/* keepalive %rsi */
	call	_pypy_g___mm_gt_0_perform_call
	;; expected {88(%rsp) | 40(%rsp), 56(%rsp), 64(%rsp), 72(%rsp), 80(%rsp), 48(%rsp) | %rbx, %rbp}
	movq	___gcmapend@GOTPCREL(%rip), %rdx
	movq	%rbx, %r15
	/* GCROOT %r15 */
	movq	%rbp, %r14
	/* GCROOT %r14 */
	movq	%rbx, %r12
	/* GCROOT %r12 */
	/* GCROOT %rbp */
	movq	_pypy_g_ExcData@GOTPCREL(%rip), %r11
	movq	(%r11), %rbx
	testq	%rbx, %rbx
	je	L981
L1016:
	movq	8(%r11), %r13
	movq	_pypydtcount@GOTPCREL(%rip), %r10
	movl	(%r10), %eax
	movq	_pypy_debug_tracebacks@GOTPCREL(%rip), %r9
	movslq	%eax,%rdx
	salq	$4, %rdx
	leaq	_loc.235018(%rip), %rcx
	movq	%rcx, (%rdx,%r9)
	movq	%rbx, 8(%rdx,%r9)
	incl	%eax
	andl	$127, %eax
	movl	%eax, (%r10)
	movq	_pypy_g_typeinfo@GOTPCREL(%rip), %r8
	leaq	59688(%r8), %rax
	cmpq	%rax, %rbx
	je	L1018
	leaq	59544(%r8), %rax
	cmpq	%rax, %rbx
	je	L1018
L1020:
	movq	$0, 8(%r11)
	movq	$0, (%r11)
	/* keepalive %r13 */
	/* keepalive %r15 */
	/* keepalive %r14 */
	/* keepalive %rbp */
	/* keepalive %r12 */
L1021:
	movq	1712(%r8), %rcx
	movq	(%rbx), %rdx
	subq	%rcx, %rdx
	movq	1720(%r8), %rax
L1022:
	/* GC_NOCOLLECT pypy_g_ll_issubclass */
	subq	%rcx, %rax
	cmpq	%rax, %rdx
	jae	L1062
L1023:
	/* keepalive %r12 */
	/* keepalive %rbp */
	movq	%rbp, %rsi
	movq	%r12, %rdi
	movq	40(%rsp), %rbx
	movq	48(%rsp), %rbp
	movq	56(%rsp), %r12
	movq	64(%rsp), %r13
	movq	72(%rsp), %r14
	movq	80(%rsp), %r15
	addq	$88, %rsp
	jmp	_pypy_g_comparison_gt_impl
L977:
	/* keepalive %rdi */
	/* keepalive %rsi */
	call	_pypy_g___mm_ge_0_perform_call
	;; expected {88(%rsp) | 40(%rsp), 56(%rsp), 64(%rsp), 72(%rsp), 80(%rsp), 48(%rsp) | %rbx, %rbp}
	movq	___gcmapend@GOTPCREL(%rip), %rdx
	movq	%rbx, %r15
	/* GCROOT %r15 */
	movq	%rbp, %r14
	/* GCROOT %r14 */
	movq	%rbx, %r12
	/* GCROOT %r12 */
	/* GCROOT %rbp */
	movq	_pypy_g_ExcData@GOTPCREL(%rip), %r11
	movq	(%r11), %rbx
	testq	%rbx, %rbx
	je	L981
L1025:
	movq	8(%r11), %r13
	movq	_pypydtcount@GOTPCREL(%rip), %r10
	movl	(%r10), %eax
	movq	_pypy_debug_tracebacks@GOTPCREL(%rip), %r9
	movslq	%eax,%rdx
	salq	$4, %rdx
	leaq	_loc.235030(%rip), %rcx
	movq	%rcx, (%rdx,%r9)
	movq	%rbx, 8(%rdx,%r9)
	incl	%eax
	andl	$127, %eax
	movl	%eax, (%r10)
	movq	_pypy_g_typeinfo@GOTPCREL(%rip), %r8
	leaq	59688(%r8), %rax
	cmpq	%rax, %rbx
	je	L1027
	leaq	59544(%r8), %rax
	cmpq	%rax, %rbx
	je	L1027
L1029:
	movq	$0, 8(%r11)
	movq	$0, (%r11)
	/* keepalive %r13 */
	/* keepalive %r15 */
	/* keepalive %r14 */
	/* keepalive %r12 */
	/* keepalive %rbp */
L1030:
	movq	1712(%r8), %rcx
	movq	(%rbx), %rdx
	subq	%rcx, %rdx
	movq	1720(%r8), %rax
L1031:
	/* GC_NOCOLLECT pypy_g_ll_issubclass */
	subq	%rcx, %rax
	cmpq	%rax, %rdx
	jae	L1063
L1032:
	/* keepalive %r12 */
	/* keepalive %rbp */
	movq	%rbp, %rsi
	movq	%r12, %rdi
	movq	40(%rsp), %rbx
	movq	48(%rsp), %rbp
	movq	56(%rsp), %r12
	movq	64(%rsp), %r13
	movq	72(%rsp), %r14
	movq	80(%rsp), %r15
	addq	$88, %rsp
	jmp	_pypy_g_comparison_ge_impl
L1045:
L1034:
	movl	$16, %esi
	call	_pypy_g_MiniMarkGC_collect_and_reserve
	;; expected {88(%rsp) | 40(%rsp), 56(%rsp), 64(%rsp), 72(%rsp), 80(%rsp), 48(%rsp) | }
	movq	_pypy_g_ExcData@GOTPCREL(%rip), %r11
	movq	%rax, %rdx
	movq	%rax, %rbx
	cmpq	$0, (%r11)
	je	L1036
L1053:
	movq	_pypydtcount@GOTPCREL(%rip), %rsi
	movl	(%rsi), %edx
	movq	_pypy_debug_tracebacks@GOTPCREL(%rip), %rcx
	movslq	%edx,%rax
	salq	$4, %rax
	leaq	_loc.235064(%rip), %rbx
	movq	%rbx, (%rax,%rcx)
	movq	$0, 8(%rcx,%rax)
	incl	%edx
	andl	$127, %edx
L1052:
	movslq	%edx,%rax
	salq	$4, %rax
	leaq	_loc.235062(%rip), %rbx
	movq	%rbx, (%rax,%rcx)
	movq	$0, 8(%rax,%rcx)
	incl	%edx
	andl	$127, %edx
	movl	%edx, (%rsi)
	xorl	%eax, %eax
	jmp	L981
L1027:
	movq	%r8, 24(%rsp)
	movq	%r9, 16(%rsp)
	movq	%r10, 8(%rsp)
	movq	%r11, (%rsp)
	call	_pypy_debug_catch_fatal_exception
	;; expected {88(%rsp) | 40(%rsp), 56(%rsp), 64(%rsp), 72(%rsp), 80(%rsp), 48(%rsp) | }
	movq	(%rsp), %r11
	movq	8(%rsp), %r10
	movq	16(%rsp), %r9
	movq	24(%rsp), %r8
	jmp	L1029
L1018:
	movq	%r8, 24(%rsp)
	movq	%r9, 16(%rsp)
	movq	%r10, 8(%rsp)
	movq	%r11, (%rsp)
	call	_pypy_debug_catch_fatal_exception
	;; expected {88(%rsp) | 40(%rsp), 56(%rsp), 64(%rsp), 72(%rsp), 80(%rsp), 48(%rsp) | }
	movq	(%rsp), %r11
	movq	8(%rsp), %r10
	movq	16(%rsp), %r9
	movq	24(%rsp), %r8
	jmp	L1020
L1009:
	movq	%r8, 24(%rsp)
	movq	%r9, 16(%rsp)
	movq	%r10, 8(%rsp)
	movq	%r11, (%rsp)
	call	_pypy_debug_catch_fatal_exception
	;; expected {88(%rsp) | 40(%rsp), 56(%rsp), 64(%rsp), 72(%rsp), 80(%rsp), 48(%rsp) | }
	movq	(%rsp), %r11
	movq	8(%rsp), %r10
	movq	16(%rsp), %r9
	movq	24(%rsp), %r8
	jmp	L1011
L1000:
	movq	%r8, 24(%rsp)
	movq	%r9, 16(%rsp)
	movq	%r10, 8(%rsp)
	movq	%r11, (%rsp)
	call	_pypy_debug_catch_fatal_exception
	;; expected {88(%rsp) | 40(%rsp), 56(%rsp), 64(%rsp), 72(%rsp), 80(%rsp), 48(%rsp) | }
	movq	(%rsp), %r11
	movq	8(%rsp), %r10
	movq	16(%rsp), %r9
	movq	24(%rsp), %r8
	jmp	L1002
L991:
	movq	%r8, 24(%rsp)
	movq	%r9, 16(%rsp)
	movq	%r10, 8(%rsp)
	movq	%r11, (%rsp)
	call	_pypy_debug_catch_fatal_exception
	;; expected {88(%rsp) | 40(%rsp), 56(%rsp), 64(%rsp), 72(%rsp), 80(%rsp), 48(%rsp) | }
	movq	(%rsp), %r11
	movq	8(%rsp), %r10
	movq	16(%rsp), %r9
	movq	24(%rsp), %r8
	jmp	L993
L982:
	movq	%r8, 24(%rsp)
	movq	%r9, 16(%rsp)
	movq	%r10, 8(%rsp)
	movq	%r11, (%rsp)
	call	_pypy_debug_catch_fatal_exception
	;; expected {88(%rsp) | 40(%rsp), 56(%rsp), 64(%rsp), 72(%rsp), 80(%rsp), 48(%rsp) | }
	movq	(%rsp), %r11
	movq	8(%rsp), %r10
	movq	16(%rsp), %r9
	movq	24(%rsp), %r8
	jmp	L984
L1059:
L997:
	movq	%rbx, (%r11)
	movq	%r13, 8(%r11)
	movl	(%r10), %edx
	movslq	%edx,%rax
	salq	$4, %rax
	movq	$-1, (%rax,%r9)
	movq	%rbx, 8(%rax,%r9)
	incl	%edx
	andl	$127, %edx
	movl	%edx, (%r10)
	/* GC_NOCOLLECT pypy_g_RPyReRaiseException */
	xorl	%eax, %eax
	jmp	L981
L1058:
L988:
	movq	%rbx, (%r11)
	movq	%r13, 8(%r11)
	movl	(%r10), %edx
	movslq	%edx,%rax
	salq	$4, %rax
	movq	$-1, (%rax,%r9)
	movq	%rbx, 8(%rax,%r9)
	incl	%edx
	andl	$127, %edx
	movl	%edx, (%r10)
	/* GC_NOCOLLECT pypy_g_RPyReRaiseException */
	xorl	%eax, %eax
	jmp	L981
L1061:
L1015:
	movq	%rbx, (%r11)
	movq	%r13, 8(%r11)
	movl	(%r10), %edx
	movslq	%edx,%rax
	salq	$4, %rax
	movq	$-1, (%rax,%r9)
	movq	%rbx, 8(%rax,%r9)
	incl	%edx
	andl	$127, %edx
	movl	%edx, (%r10)
	/* GC_NOCOLLECT pypy_g_RPyReRaiseException */
	xorl	%eax, %eax
	jmp	L981
L1060:
L1006:
	movq	%rbx, (%r11)
	movq	%r13, 8(%r11)
	movl	(%r10), %edx
	movslq	%edx,%rax
	salq	$4, %rax
	movq	$-1, (%rax,%r9)
	movq	%rbx, 8(%rax,%r9)
	incl	%edx
	andl	$127, %edx
	movl	%edx, (%r10)
	/* GC_NOCOLLECT pypy_g_RPyReRaiseException */
	xorl	%eax, %eax
	jmp	L981
L1063:
L1033:
	movq	%rbx, (%r11)
	movq	%r13, 8(%r11)
	movl	(%r10), %edx
	movslq	%edx,%rax
	salq	$4, %rax
	movq	$-1, (%rax,%r9)
	movq	%rbx, 8(%rax,%r9)
	incl	%edx
	andl	$127, %edx
	movl	%edx, (%r10)
	/* GC_NOCOLLECT pypy_g_RPyReRaiseException */
	xorl	%eax, %eax
	jmp	L981
L1062:
L1024:
	movq	%rbx, (%r11)
	movq	%r13, 8(%r11)
	movl	(%r10), %edx
	movslq	%edx,%rax
	salq	$4, %rax
	movq	$-1, (%rax,%r9)
	movq	%rbx, 8(%rax,%r9)
	incl	%edx
	andl	$127, %edx
	movl	%edx, (%r10)
	/* GC_NOCOLLECT pypy_g_RPyReRaiseException */
	xorl	%eax, %eax
	jmp	L981
L1040:
	movq	%r8, 24(%rsp)
	movq	%r9, 16(%rsp)
	movq	%r10, 8(%rsp)
	movq	%r11, (%rsp)
	call	_pypy_debug_catch_fatal_exception
	;; expected {88(%rsp) | 40(%rsp), 56(%rsp), 64(%rsp), 72(%rsp), 80(%rsp), 48(%rsp) | }
	movq	(%rsp), %r11
	movq	8(%rsp), %r10
	movq	16(%rsp), %r9
	movq	24(%rsp), %r8
	jmp	L1042
L1048:
	/* keepalive %rbx */
	/* keepalive %r12 */
L1051:
	movq	%rbp, (%r11)
	movq	%r12, 8(%r11)
	movl	(%r10), %edx
	movslq	%edx,%rax
	salq	$4, %rax
	movq	$-1, (%rax,%r9)
	movq	%rbp, 8(%rax,%r9)
	incl	%edx
	andl	$127, %edx
	movl	%edx, (%r10)
	/* GC_NOCOLLECT pypy_g_RPyReRaiseException */
	xorl	%eax, %eax
	jmp	L981
L1057:
L1039:
	movq	_pypy_g_typeinfo@GOTPCREL(%rip), %rsi
	addq	$59688, %rsi
	movq	%rsi, (%r11)
	movq	_pypy_g_exceptions_AssertionError_5@GOTPCREL(%rip), %rax
	movq	%rax, 8(%r11)
	movq	_pypydtcount@GOTPCREL(%rip), %rdi
	movl	(%rdi), %edx
	movq	_pypy_debug_tracebacks@GOTPCREL(%rip), %rcx
	movslq	%edx,%rax
	salq	$4, %rax
	movq	$0, (%rax,%rcx)
	movq	%rsi, 8(%rcx,%rax)
	incl	%edx
	andl	$127, %edx
	/* GC_NOCOLLECT pypy_g_RPyRaiseException */
	movslq	%edx,%rax
	salq	$4, %rax
	leaq	_loc.235054(%rip), %rbx
	movq	%rbx, (%rax,%rcx)
	movq	$0, 8(%rcx,%rax)
	incl	%edx
	andl	$127, %edx
	movl	%edx, (%rdi)
	xorl	%eax, %eax
	jmp	L981
LFE302:
	.align 4,0x90
