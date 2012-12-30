_pypy_g_MetaInterp_prepare_resume_from_failure:
	subl	$28, %esp
	movl	%ebx, 20(%esp)
	movl	%esi, 24(%esp)
	call	L2245
"L00000000130$pb":
L2245:
	popl	%ebx
	movl	32(%esp), %edx
L2231:
	movl	36(%esp), %eax
	subl	$6, %eax
	cmpl	$7, %eax
	jbe	L2244
L2243:
	movl	20(%esp), %ebx
	movl	24(%esp), %esi
	addl	$28, %esp
	ret
	.align 4,0x90
L2244:
	movl	L2237-"L00000000130$pb"(%ebx,%eax,4), %eax
	addl	%ebx, %eax
	jmp	*%eax
	.align 2,0x90
L2237:
	.long	L2233-"L00000000130$pb"
	.long	L2234-"L00000000130$pb"
	.long	L2243-"L00000000130$pb"
	.long	L2243-"L00000000130$pb"
	.long	L2243-"L00000000130$pb"
	.long	L2235-"L00000000130$pb"
	.long	L2235-"L00000000130$pb"
	.long	L2236-"L00000000130$pb"
L2236:
	movl	%edx, 32(%esp)
	movl	20(%esp), %ebx
	movl	24(%esp), %esi
	addl	$28, %esp
	jmp	L_pypy_g_MetaInterp_raise_overflow_error$stub
L2235:
	movl	%edx, 32(%esp)
	movl	20(%esp), %ebx
	movl	24(%esp), %esi
	addl	$28, %esp
	jmp	L_pypy_g_MetaInterp_handle_exception$stub
L2234:
	movl	16(%edx), %eax
	movl	8(%eax), %edx
	movl	4(%eax), %eax
	movl	4(%edx,%eax,4), %eax
	movl	%eax, 32(%esp)
	movl	20(%esp), %ebx
	movl	24(%esp), %esi
	addl	$28, %esp
	jmp	L_pypy_g_MIFrame_dont_follow_jump$stub
L2233:
	movl	16(%edx), %eax
	movl	8(%eax), %edx
	movl	4(%eax), %eax
	movl	4(%edx,%eax,4), %esi
	movl	8(%esi), %ecx
	movl	52(%esi), %eax
	testl	%eax, %eax
	js	L2238
	movl	%eax, %edx
L2240:
	cmpb	$0, 12(%ecx,%edx)
	je	L2241
L2242:
	movl	L_pypy_g_exceptions_AssertionError$non_lazy_ptr-"L00000000130$pb"(%ebx), %eax
	movl	%eax, 36(%esp)
	movl	L_pypy_g_exceptions_AssertionError_vtable$non_lazy_ptr-"L00000000130$pb"(%ebx), %eax
	movl	%eax, 32(%esp)
	movl	20(%esp), %ebx
	movl	24(%esp), %esi
	addl	$28, %esp
	jmp	L_pypy_g_RPyRaiseException$stub
L2241:
	incl	%eax
	movl	%eax, 52(%esi)
	movl	%esi, (%esp)
	call	L_pypy_g_MIFrame_load_3byte$stub
        ;; expected {28(%esp) | 20(%esp), 24(%esp), %edi, %ebp | }
	movl	%eax, 52(%esi)
	movl	20(%esp), %ebx
	movl	24(%esp), %esi
	addl	$28, %esp
	ret
L2238:
	movl	%eax, %edx
	addl	8(%ecx), %edx
	jmp	L2240
	.align 4,0x90
