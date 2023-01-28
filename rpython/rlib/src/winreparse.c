// #define WIN32_LEAN_AND_MEAN // FSCTL_GET_REPARSE_POINT is not defined in LEAN_AND_MEAN
#include <windows.h>
#include <winreparse.h>
#include <stdio.h>

#ifndef RPY_EXPORTED
#ifdef __GNUC__
#  define RPY_EXPORTED extern __attribute__((visibility("default")))
#else
#  define RPY_EXPORTED extern __declspec(dllexport)
#endif
#endif

static void __cdecl _silent_invalid_parameter_handler(
    wchar_t const* expression,
    wchar_t const* function,
    wchar_t const* file,
    unsigned int line,
    uintptr_t pReserved) { }

#define _BEGIN_SUPPRESS_IPH { _invalid_parameter_handler _old_handler = \
    _set_thread_local_invalid_parameter_handler(_silent_invalid_parameter_handler);
#define _END_SUPPRESS_IPH _set_thread_local_invalid_parameter_handler(_old_handler); }



void* enter_suppress_iph();
void exit_suppress_iph(void* handle);

RPY_EXPORTED int
os_readlink_impl(wchar_t *path_wide, void *target_buffer, wchar_t **result) {
    DWORD n_bytes_returned;
    DWORD io_result = 0;
    HANDLE reparse_point_handle;
    _Py_REPARSE_DATA_BUFFER *rdb = (_Py_REPARSE_DATA_BUFFER *)target_buffer;

    /* First get a handle to the reparse point */
    reparse_point_handle = CreateFileW(
        path_wide,
        0,
        0,
        0,
        OPEN_EXISTING,
        FILE_FLAG_OPEN_REPARSE_POINT|FILE_FLAG_BACKUP_SEMANTICS,
        0);
    if (reparse_point_handle != INVALID_HANDLE_VALUE) {
        /* New call DeviceIoControl to read the reparse point */
        io_result = DeviceIoControl(
            reparse_point_handle,
            FSCTL_GET_REPARSE_POINT,
            0, 0, /* in buffer */
            target_buffer, _Py_MAXIMUM_REPARSE_DATA_BUFFER_SIZE,
            &n_bytes_returned,
            0 /* we're not using OVERLAPPED_IO */
            );
        CloseHandle(reparse_point_handle);
    }

    if (io_result == 0) {
        return -1;
    }

    long nameLen = 0;
    if (rdb->ReparseTag == IO_REPARSE_TAG_SYMLINK)
    {
        result[0] = (wchar_t *)((char*)rdb->SymbolicLinkReparseBuffer.PathBuffer +
                           rdb->SymbolicLinkReparseBuffer.SubstituteNameOffset);
        nameLen = rdb->SymbolicLinkReparseBuffer.SubstituteNameLength / sizeof(wchar_t);
    }
    else if (rdb->ReparseTag == IO_REPARSE_TAG_MOUNT_POINT)
    {
        result[0] = (wchar_t*)((char*)rdb->MountPointReparseBuffer.PathBuffer +
                           rdb->MountPointReparseBuffer.SubstituteNameOffset);
        nameLen = rdb->MountPointReparseBuffer.SubstituteNameLength / sizeof(wchar_t);
    }
    else
    {
        result[0] = NULL;
        return -2;
    }
    if (nameLen > 4 && wcsncmp(result[0], L"\\??\\", 4) == 0) {
        result[0][1] = L'\\';
    }
    return (int)nameLen;
}

/* Remove the last portion of the path - return 0 on success */
static int
_dirnameW(WCHAR *path)
{
    WCHAR *ptr;
    size_t length = wcsnlen_s(path, MAX_PATH);
    if (length == MAX_PATH) {
        return -1;
    }

    /* walk the path from the end until a backslash is encountered */
    for(ptr = path + length; ptr != path; ptr--) {
        if (*ptr == L'\\' || *ptr == L'/') {
            break;
        }
    }
    *ptr = 0;
    return 0;
}

/* Is this path absolute? */
static int
_is_absW(const WCHAR *path)
{
    return path[0] == L'\\' || path[0] == L'/' ||
        (path[0] && path[1] == L':');
}

/* join root and rest with a backslash - return 0 on success */
static int
_joinW(WCHAR *dest_path, const WCHAR *root, const WCHAR *rest)
{
    if (_is_absW(rest)) {
        return wcscpy_s(dest_path, MAX_PATH, rest);
    }

    if (wcscpy_s(dest_path, MAX_PATH, root)) {
        return -1;
    }

    if (dest_path[0] && wcscat_s(dest_path, MAX_PATH, L"\\")) {
        return -1;
    }

    return wcscat_s(dest_path, MAX_PATH, rest);
}

/* Return True if the path at src relative to dest is a directory */
static int
_check_dirW(LPCWSTR src, LPCWSTR dest)
{
    WIN32_FILE_ATTRIBUTE_DATA src_info;
    WCHAR dest_parent[MAX_PATH];
    WCHAR src_resolved[MAX_PATH] = L"";

    /* dest_parent = os.path.dirname(dest) */
    if (wcscpy_s(dest_parent, MAX_PATH, dest) ||
        _dirnameW(dest_parent)) {
        return 0;
    }
    /* src_resolved = os.path.join(dest_parent, src) */
    if (_joinW(src_resolved, dest_parent, src)) {
        return 0;
    }
    return (
        GetFileAttributesExW(src_resolved, GetFileExInfoStandard, &src_info)
        && src_info.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY
    );
}

RPY_EXPORTED int
os_symlink_impl(wchar_t *src, wchar_t *dst, int target_is_directory)
{
    DWORD result;
    DWORD flags = 0;

    /* Assumed true, set to false if detected to not be available. */
    static int windows_has_symlink_unprivileged_flag = TRUE;
    if (windows_has_symlink_unprivileged_flag) {
        /* Allow non-admin symlinks if system allows it. */
        flags |= SYMBOLIC_LINK_FLAG_ALLOW_UNPRIVILEGED_CREATE;
    }

    _BEGIN_SUPPRESS_IPH
    /* if src is a directory, ensure flags==1 (target_is_directory bit) */
    if (target_is_directory || _check_dirW(src, dst)) {
        flags |= SYMBOLIC_LINK_FLAG_DIRECTORY;
    }

    result = CreateSymbolicLinkW(dst, src, flags);
    _END_SUPPRESS_IPH

    if (windows_has_symlink_unprivileged_flag && !result &&
        ERROR_INVALID_PARAMETER == GetLastError()) {

        _BEGIN_SUPPRESS_IPH
        /* This error might be caused by
        SYMBOLIC_LINK_FLAG_ALLOW_UNPRIVILEGED_CREATE not being supported.
        Try again, and update windows_has_symlink_unprivileged_flag if we
        are successful this time.

        NOTE: There is a risk of a race condition here if there are other
        conditions than the flag causing ERROR_INVALID_PARAMETER, and
        another process (or thread) changes that condition in between our
        calls to CreateSymbolicLink.
        */
        flags &= ~(SYMBOLIC_LINK_FLAG_ALLOW_UNPRIVILEGED_CREATE);
        result = CreateSymbolicLinkW(dst, src, flags);
        _END_SUPPRESS_IPH

        if (result || ERROR_INVALID_PARAMETER != GetLastError()) {
            windows_has_symlink_unprivileged_flag = FALSE;
        }
    }
    return (int)result;
}
