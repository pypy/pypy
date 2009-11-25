	.type	pypy_g_populate, @function
pypy_g_populate:
	pushl	%esi
	pushl	%ebx
	subl	$20, %esp
	movl	32(%esp), %esi
	movl	36(%esp), %ebx
	jmp	.L1387
	.p2align 4,,7
.L1416:
.L1371:
.L1374:
	movl	$31, 4(%edx)
	leal	24(%edx), %eax
	movl	$pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC, %ecx
	movl	%eax, 12(%ecx)
	movl	%edx, %eax
.L1375:
#APP
	/* GCROOT %ebx */
#NO_APP
	testl	%eax, %eax
	je	.L1345
.L1377:
	movl	$0, 12(%eax)
	movl	pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC+12, %edx
	movl	pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC+72, %ecx
	movl	$pypy_g_pypy_translator_goal_gcbench_Node_vtable, 8(%eax)
	movl	$0, 16(%eax)
	subl	%edx, %ecx
	cmpl	$23, %ecx
	movl	%eax, 12(%ebx)
	jle	.L1415
.L1417:
.L1380:
.L1383:
	movl	$31, 4(%edx)
	leal	24(%edx), %eax
	movl	$pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC, %ecx
	movl	%eax, 12(%ecx)
	movl	%edx, %eax
.L1384:
#APP
	/* GCROOT %ebx */
#NO_APP
	testl	%eax, %eax
	je	.L1345
.L1386:
	movl	$0, 12(%eax)
	movl	12(%ebx), %edx
	movl	$0, 16(%eax)
	movl	$pypy_g_pypy_translator_goal_gcbench_Node_vtable, 8(%eax)
	movl	%eax, 16(%ebx)
	movl	%edx, 4(%esp)
	movl	%esi, (%esp)
	call	pypy_g_populate
        ;; expected {28(%esp) | 20(%esp), 24(%esp), %edi, %ebp | %ebx}
	movl	%ebx, %eax
#APP
	/* GCROOT %eax */
#NO_APP
	movl	pypy_g_ExcData, %ebx
	testl	%ebx, %ebx
	jne	.L1345
.L1389:
	movl	16(%eax), %ebx
.L1387:
.L1346:
	testl	%esi, %esi
	jle	.L1345
.L1349:
.L1350:
.L1351:
.L1352:
	call	LL_stack_too_big
        ;; expected {28(%esp) | 20(%esp), 24(%esp), %edi, %ebp | %ebx}
	testl	%eax, %eax
	jne	.L1418
.L1361:
.L1363:
.L1365:
.L1357:
#APP
	/* GCROOT %ebx */
#NO_APP
	movl	pypy_g_ExcData, %ecx
	testl	%ecx, %ecx
	jne	.L1345
.L1368:
	movl	pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC+12, %edx
	decl	%esi
	movl	pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC+72, %eax
	subl	%edx, %eax
	cmpl	$23, %eax
	jg	.L1416
.L1373:
.L1370:
.L1402:
	movl	$pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC, (%esp)
	movl	$24, %edx
	movl	%edx, 4(%esp)
	call	pypy_g_SemiSpaceGC_try_obtain_free_space
        ;; expected {28(%esp) | 20(%esp), 24(%esp), %edi, %ebp | %ebx}
	movl	pypy_g_ExcData, %edx
	xorl	%ecx, %ecx
	testl	%edx, %edx
	je	.L1419
.L1404:
	xorl	%eax, %eax
	testl	%edx, %edx
	jne	.L1375
	movl	%ecx, %edx
	jmp	.L1416
.L1348:
.L1382:
	.p2align 4,,7
.L1415:
.L1379:
.L1390:
	movl	$pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC, (%esp)
	movl	$24, %ecx
	movl	%ecx, 4(%esp)
	call	pypy_g_SemiSpaceGC_try_obtain_free_space
        ;; expected {28(%esp) | 20(%esp), 24(%esp), %edi, %ebp | %ebx}
	movl	pypy_g_ExcData, %edx
	xorl	%ecx, %ecx
	testl	%edx, %edx
	je	.L1420
.L1392:
	xorl	%eax, %eax
	testl	%edx, %edx
	jne	.L1384
	movl	%ecx, %edx
	jmp	.L1417
.L1345:
	addl	$20, %esp
	popl	%ebx
	popl	%esi
	ret
.L1356:
.L1355:
.L1358:
.L1359:
.L1360:
.L1418:
	movl	$pypy_g_exceptions_RuntimeError_vtable, %edx
	movl	$pypy_g_exceptions_RuntimeError, %eax
	movl	%edx, pypy_g_ExcData
	movl	%eax, pypy_g_ExcData+4
	jmp	.L1357
.L1419:
.L1405:
	testb	%al, %al
	je	.L1421
.L1407:
	movl	pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC+12, %ecx
	jmp	.L1404
.L1420:
.L1393:
	testb	%al, %al
	je	.L1422
.L1395:
	movl	pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC+12, %ecx
	jmp	.L1392
.L1408:
.L1409:
.L1421:
.L1410:
	movl	$pypy_g_exceptions_MemoryError_vtable, %edx
	movl	$pypy_g_exceptions_MemoryError_1, %eax
	movl	%edx, pypy_g_ExcData
	movl	%eax, pypy_g_ExcData+4
	jmp	.L1404
.L1396:
.L1397:
.L1422:
.L1398:
	movl	$pypy_g_exceptions_MemoryError_vtable, %edx
	movl	$pypy_g_exceptions_MemoryError_1, %eax
	movl	%edx, pypy_g_ExcData
	movl	%eax, pypy_g_ExcData+4
	jmp	.L1392
	.size	pypy_g_populate, .-pypy_g_populate
