_pypy_g_foo:
L1506:
	subl	$140, %esp
	movl	%esi, 128(%esp)
	movl	144(%esp), %esi
	movl	%ebx, 124(%esp)
	call	L1534
"L00000000044$pb":
L1534:
	popl	%ebx
	movl	%edi, 132(%esp)
	testl	%esi, %esi
	movl	%ebp, 136(%esp)
	jle	L1529
L1508:
L1509:
	movl	L__LLstacktoobig_stack_base_pointer$non_lazy_ptr-"L00000000044$pb"(%ebx), %eax
	leal	111(%esp), %edx
	subl	(%eax), %edx
	movl	L__LLstacktoobig_stack_min$non_lazy_ptr-"L00000000044$pb"(%ebx), %eax
	cmpl	(%eax), %edx
	jl	L1510
	movl	L__LLstacktoobig_stack_max$non_lazy_ptr-"L00000000044$pb"(%ebx), %eax
	cmpl	(%eax), %edx
	jg	L1510
L1531:
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000044$pb"(%ebx), %esi
	movl	(%esi), %ecx
	testl	%ecx, %ecx
	je	L1532
L1529:
	movl	124(%esp), %ebx
	movl	128(%esp), %esi
	movl	132(%esp), %edi
	movl	136(%esp), %ebp
	addl	$140, %esp
	ret
	.align 4,0x90
L1510:
	call	L_LL_stack_too_big_slowpath$stub
        ;; expected {140(%esp) | 124(%esp), 128(%esp), 132(%esp), 136(%esp) | 148(%esp), 152(%esp), 156(%esp), 160(%esp), 164(%esp), 168(%esp)}
	testl	%eax, %eax
	je	L1531
L1513:
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000044$pb"(%ebx), %esi
	movl	L_pypy_g_exceptions_RuntimeError_vtable$non_lazy_ptr-"L00000000044$pb"(%ebx), %eax
	movl	%eax, (%esi)
	movl	(%esi), %ecx
	movl	L_pypy_g_exceptions_RuntimeError$non_lazy_ptr-"L00000000044$pb"(%ebx), %eax
	testl	%ecx, %ecx
	movl	%eax, 4(%esi)
	jne	L1529
L1514:
	.align 4,0x90
L1532:
	movl	L_pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC$non_lazy_ptr-"L00000000044$pb"(%ebx), %edi
	movl	12(%edi), %edx
	movl	80(%edi), %eax
	subl	%edx, %eax
	cmpl	$7, %eax
	jle	L1515
L1517:
	leal	8(%edx), %eax
	movl	$4, (%edx)
	movl	%eax, 12(%edi)
	movl	%edx, %edi
L1518:
	movl	L___gcnoreorderhack$non_lazy_ptr-"L00000000044$pb"(%ebx), %esi
	movl	168(%esp), %eax
	movl	164(%esp), %ebp
	/* GCROOT %eax */
	/* GCROOT %ebp */
	movl	%eax, 48(%esp)
	movl	152(%esp), %eax
	/* GCROOT %eax */
	movl	%eax, 52(%esp)
	movl	156(%esp), %eax
	/* GCROOT %eax */
	movl	%eax, 56(%esp)
	movl	160(%esp), %eax
	/* GCROOT %eax */
	movl	%eax, 60(%esp)
	movl	148(%esp), %eax
	/* GCROOT %eax */
	testl	%edx, %edx
	movl	%eax, 64(%esp)
	je	L1529
L1519:
	movl	L_pypy_g_src8_A_vtable$non_lazy_ptr-"L00000000044$pb"(%ebx), %eax
	movl	%eax, 4(%edi)
	movl	144(%esp), %edx
	movl	%edi, 24(%esp)
	movl	%edi, 20(%esp)
	movl	%edi, 16(%esp)
	decl	%edx
	movl	%edx, 44(%esp)
	movl	%edi, 12(%esp)
	movl	%edi, 8(%esp)
	movl	%edi, 4(%esp)
	movl	%edx, (%esp)
	call	_pypy_g_foo
        ;; expected {140(%esp) | 124(%esp), 128(%esp), 132(%esp), 136(%esp) | %edi, %ebp, 48(%esp), 52(%esp), 56(%esp), 60(%esp), 64(%esp)}
	movl	56(%esp), %edx
	/* GCROOT %edx */
	movl	%edx, 76(%esp)
	movl	60(%esp), %edx
	/* GCROOT %edx */
	movl	%edx, 80(%esp)
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000044$pb"(%ebx), %edx
	/* GCROOT %ebp */
	movl	48(%esp), %eax
	movl	%ebp, 72(%esp)
	movl	52(%esp), %ebp
	movl	(%edx), %edx
	/* GCROOT %eax */
	/* GCROOT %ebp */
	movl	%eax, 68(%esp)
	movl	%edi, %eax
	movl	64(%esp), %edi
	/* GCROOT %eax */
	/* GCROOT %edi */
	testl	%edx, %edx
	jne	L1529
L1520:
	movl	%eax, 24(%esp)
	movl	%eax, 20(%esp)
	movl	%eax, 16(%esp)
	movl	%eax, 12(%esp)
	movl	%eax, 8(%esp)
	movl	%eax, 4(%esp)
	movl	44(%esp), %eax
	movl	%eax, (%esp)
	call	_pypy_g_foo
        ;; expected {140(%esp) | 124(%esp), 128(%esp), 132(%esp), 136(%esp) | %edi, %ebp, 68(%esp), 72(%esp), 76(%esp), 80(%esp)}
	movl	68(%esp), %edx
	movl	72(%esp), %eax
	/* GCROOT %edx */
	/* GCROOT %eax */
	movl	%edx, 84(%esp)
	movl	80(%esp), %ecx
	movl	%eax, 88(%esp)
	movl	76(%esp), %edx
	movl	%edi, %eax
	/* GCROOT %edx */
	/* GCROOT %ecx */
	/* GCROOT %eax */
	movl	%edx, 92(%esp)
	movl	%ebp, %edx
	/* GCROOT %edx */
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000044$pb"(%ebx), %esi
	movl	(%esi), %esi
	testl	%esi, %esi
	jne	L1529
L1521:
	movl	%eax, 24(%esp)
	movl	92(%esp), %eax
	movl	%edx, 20(%esp)
	movl	84(%esp), %esi
	movl	88(%esp), %edx
	movl	%ecx, 12(%esp)
	movl	%eax, 16(%esp)
	movl	44(%esp), %eax
	movl	%esi, 4(%esp)
	movl	%edx, 8(%esp)
	movl	%eax, (%esp)
	call	_pypy_g_foo
        ;; expected {140(%esp) | 124(%esp), 128(%esp), 132(%esp), 136(%esp) | }
	jmp	L1529
	.align 4,0x90
L1515:
	movl	$8, 4(%esp)
	movl	%edi, (%esp)
	call	_pypy_g_SemiSpaceGC_try_obtain_free_space
        ;; expected {140(%esp) | 124(%esp), 128(%esp), 132(%esp), 136(%esp) | 148(%esp), 152(%esp), 156(%esp), 160(%esp), 164(%esp), 168(%esp)}
	movl	(%esi), %edx
	xorl	%ecx, %ecx
	testl	%edx, %edx
	je	L1533
L1524:
	movl	L_pypy_g_ExcData$non_lazy_ptr-"L00000000044$pb"(%ebx), %eax
	xorl	%edx, %edx
	xorl	%edi, %edi
	movl	(%eax), %eax
	testl	%eax, %eax
	jne	L1518
	movl	L_pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC$non_lazy_ptr-"L00000000044$pb"(%ebx), %edi
	movl	%ecx, %edx
	jmp	L1517
L1533:
L1522:
	testb	%al, %al
	jne	L1525
L1526:
	movl	L_pypy_g_exceptions_MemoryError_vtable$non_lazy_ptr-"L00000000044$pb"(%ebx), %eax
	movl	%eax, (%esi)
	movl	L_pypy_g_exceptions_MemoryError_1$non_lazy_ptr-"L00000000044$pb"(%ebx), %eax
	movl	%eax, 4(%esi)
	jmp	L1524
L1525:
	movl	12(%edi), %ecx
	jmp	L1524
	.align 4,0x90