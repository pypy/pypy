	.type	pypy_g_populate, @function
pypy_g_populate:
	pushl	%ebp
	movl	%esp, %ebp
	pushl	%esi
	pushl	%ebx
	subl	$16, %esp
	movl	8(%ebp), %esi
	movl	12(%ebp), %ebx
	jmp	.L1386
	.p2align 4,,7
.L1415:
.L1370:
.L1373:
	movl	$31, 4(%edx)
	leal	24(%edx), %eax
	movl	$pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC, %ecx
	movl	%eax, 12(%ecx)
	movl	%edx, %eax
.L1374:
#APP
	/* GCROOT %ebx */
#NO_APP
	testl	%eax, %eax
	je	.L1344
.L1376:
	movl	$0, 12(%eax)
	movl	pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC+12, %edx
	movl	pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC+72, %ecx
	movl	$pypy_g_pypy_translator_goal_gcbench_Node_vtable, 8(%eax)
	movl	$0, 16(%eax)
	subl	%edx, %ecx
	cmpl	$23, %ecx
	movl	%eax, 12(%ebx)
	jle	.L1414
.L1416:
.L1379:
.L1382:
	movl	$31, 4(%edx)
	leal	24(%edx), %eax
	movl	$pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC, %ecx
	movl	%eax, 12(%ecx)
	movl	%edx, %eax
.L1383:
#APP
	/* GCROOT %ebx */
#NO_APP
	testl	%eax, %eax
	je	.L1344
.L1385:
	movl	$0, 12(%eax)
	movl	12(%ebx), %edx
	movl	$0, 16(%eax)
	movl	$pypy_g_pypy_translator_goal_gcbench_Node_vtable, 8(%eax)
	movl	%eax, 16(%ebx)
	movl	%edx, 4(%esp)
	movl	%esi, (%esp)
	call	pypy_g_populate
        ;; expected {4(%ebp) | -8(%ebp), -4(%ebp), %edi, (%ebp) | %ebx}
	movl	%ebx, %eax
#APP
	/* GCROOT %eax */
#NO_APP
	movl	pypy_g_ExcData, %ebx
	testl	%ebx, %ebx
	jne	.L1344
.L1388:
	movl	16(%eax), %ebx
.L1386:
.L1345:
	testl	%esi, %esi
	jle	.L1344
.L1348:
.L1349:
.L1350:
.L1351:
	call	LL_stack_too_big
        ;; expected {4(%ebp) | -8(%ebp), -4(%ebp), %edi, (%ebp) | %ebx}
	testl	%eax, %eax
	jne	.L1417
.L1360:
.L1362:
.L1364:
.L1356:
#APP
	/* GCROOT %ebx */
#NO_APP
	movl	pypy_g_ExcData, %ecx
	testl	%ecx, %ecx
	jne	.L1344
.L1367:
	movl	pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC+12, %edx
	decl	%esi
	movl	pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC+72, %eax
	subl	%edx, %eax
	cmpl	$23, %eax
	jg	.L1415
.L1372:
.L1369:
.L1401:
	movl	$pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC, (%esp)
	movl	$24, %edx
	movl	%edx, 4(%esp)
	call	pypy_g_SemiSpaceGC_try_obtain_free_space
        ;; expected {4(%ebp) | -8(%ebp), -4(%ebp), %edi, (%ebp) | %ebx}
	movl	pypy_g_ExcData, %edx
	xorl	%ecx, %ecx
	testl	%edx, %edx
	je	.L1418
.L1403:
	xorl	%eax, %eax
	testl	%edx, %edx
	jne	.L1374
	movl	%ecx, %edx
	jmp	.L1415
.L1347:
.L1381:
	.p2align 4,,7
.L1414:
.L1378:
.L1389:
	movl	$pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC, (%esp)
	movl	$24, %ecx
	movl	%ecx, 4(%esp)
	call	pypy_g_SemiSpaceGC_try_obtain_free_space
        ;; expected {4(%ebp) | -8(%ebp), -4(%ebp), %edi, (%ebp) | %ebx}
	movl	pypy_g_ExcData, %edx
	xorl	%ecx, %ecx
	testl	%edx, %edx
	je	.L1419
.L1391:
	xorl	%eax, %eax
	testl	%edx, %edx
	jne	.L1383
	movl	%ecx, %edx
	jmp	.L1416
.L1344:
	addl	$16, %esp
	popl	%ebx
	popl	%esi
	popl	%ebp
	ret
.L1355:
.L1354:
.L1357:
.L1358:
.L1359:
.L1417:
	movl	$pypy_g_exceptions_RuntimeError_vtable, %edx
	movl	$pypy_g_exceptions_RuntimeError, %eax
	movl	%edx, pypy_g_ExcData
	movl	%eax, pypy_g_ExcData+4
	jmp	.L1356
.L1418:
.L1404:
	testb	%al, %al
	je	.L1420
.L1406:
	movl	pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC+12, %ecx
	jmp	.L1403
.L1419:
.L1392:
	testb	%al, %al
	je	.L1421
.L1394:
	movl	pypy_g_pypy_rpython_memory_gc_semispace_SemiSpaceGC+12, %ecx
	jmp	.L1391
.L1407:
.L1408:
.L1420:
.L1409:
	movl	$pypy_g_exceptions_MemoryError_vtable, %edx
	movl	$pypy_g_exceptions_MemoryError_1, %eax
	movl	%edx, pypy_g_ExcData
	movl	%eax, pypy_g_ExcData+4
	jmp	.L1403
.L1395:
.L1396:
.L1421:
.L1397:
	movl	$pypy_g_exceptions_MemoryError_vtable, %edx
	movl	$pypy_g_exceptions_MemoryError_1, %eax
	movl	%edx, pypy_g_ExcData
	movl	%eax, pypy_g_ExcData+4
	jmp	.L1391
	.size	pypy_g_populate, .-pypy_g_populate
