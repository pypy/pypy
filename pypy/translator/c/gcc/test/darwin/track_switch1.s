_pypy_g___mm_mul_W_TransparentList_W_Root:
	pushl	%esi
	pushl	%ebx
	subl	$20, %esp
	call	L6833
"L00000000284$pb":
L6833:
	popl	%ebx
	movl	32(%esp), %edx
L6820:
	movl	4(%edx), %eax
	cmpl	$61, 20(%eax)
	je	L6821
L6822:
	movl	L_pypy_g_pypy_rpython_memory_gc_hybrid_HybridGC$non_lazy_ptr-"L00000000284$pb"(%ebx), %esi
	movl	112(%esi), %edx
	movl	124(%esi), %eax
	subl	%edx, %eax
	cmpl	$15, %eax
	jle	L6823
L6825:
	movl	$14, (%edx)
	leal	16(%edx), %eax
	movl	%eax, 112(%esi)
L6826:
	movl	L_pypy_g_pypy_objspace_std_multimethod_FailedToImplement_$non_lazy_ptr-"L00000000284$pb"(%ebx), %eax
	movl	%eax, 4(%edx)
	movl	$0, 8(%edx)
	movl	$0, 12(%edx)
	movl	%edx, 4(%esp)
	movl	4(%edx), %eax
	movl	%eax, (%esp)
	call	L_pypy_g_RPyRaiseException$stub
        ;; expected {28(%esp) | 20(%esp), 24(%esp), %edi, %ebp | }
	xorl	%ecx, %ecx
L6827:
	movl	%ecx, %eax
	addl	$20, %esp
	popl	%ebx
	popl	%esi
	ret
	.align 4,0x90
L6821:
	movl	36(%esp), %ecx
	movl	4(%ecx), %eax
	cmpl	$66, 20(%eax)
	ja	L6822
	movl	20(%eax), %eax
	movl	L6831-"L00000000284$pb"(%ebx,%eax,4), %eax
	addl	%ebx, %eax
	jmp	*%eax
	.align 2,0x90
L6831:
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6822-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6822-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6822-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6822-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.long	L6830-"L00000000284$pb"
	.align 4,0x90
L6823:
	movl	%esi, (%esp)
	call	L_pypy_g_GenerationGC_collect_nursery$stub
        ;; expected {28(%esp) | 20(%esp), 24(%esp), %edi, %ebp | }
	xorl	%ecx, %ecx
	movl	%eax, %edx
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000284$pb"(%ebx), %eax
	movl	(%eax), %eax
	testl	%eax, %eax
	je	L6825
	movl	%ecx, %eax
	addl	$20, %esp
	popl	%ebx
	popl	%esi
	ret
L6830:
	/* keepalive 36(%esp) */
	movl	36(%esp), %eax
	movl	%eax, 8(%esp)
	movl	L_pypy_g_pypy_objspace_std_stringobject_W_StringObject_574$non_lazy_ptr-"L00000000284$pb"(%ebx), %eax
	movl	%eax, 4(%esp)
	movl	8(%edx), %eax
	movl	%eax, (%esp)
	call	L_pypy_g_call_function__star_2$stub
        ;; expected {28(%esp) | 20(%esp), 24(%esp), %edi, %ebp | }
	movl	%eax, %ecx
	jmp	L6827
	.align 4,0x90
