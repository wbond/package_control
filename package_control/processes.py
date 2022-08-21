import os

__all__ = ['list_process_names']

if os.name == 'nt':
    import ctypes
    from ctypes import windll, wintypes, POINTER, sizeof, byref, cast

    psapi = windll.psapi
    kernel32 = windll.kernel32

    if not hasattr(wintypes, 'PDWORD'):
        wintypes.PDWORD = POINTER(wintypes.DWORD)
        wintypes.LPDWORD = wintypes.PDWORD

    PHModule = POINTER(wintypes.HANDLE)

    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010

    psapi.EnumProcesses.argtypes = [wintypes.PDWORD, wintypes.DWORD, wintypes.PDWORD]
    psapi.EnumProcesses.restype = wintypes.BOOL

    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE

    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    psapi.EnumProcessModules.argtypes = [wintypes.HANDLE, PHModule, wintypes.DWORD, POINTER(wintypes.LPDWORD)]
    psapi.EnumProcessModules.restype = wintypes.BOOL

    psapi.GetModuleBaseNameW.argtypes = [wintypes.HANDLE, wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD]
    psapi.GetModuleBaseNameW.restype = wintypes.DWORD

    def list_process_names():
        """
        List names of running processes.

        :return:
            A generator of process names
        """

        process_ids = []
        process_id_array_size = 1024
        entries = 0

        while entries == 0 or process_id_array_size == entries:
            dword_array = (wintypes.DWORD * process_id_array_size)

            process_ids = dword_array()
            bytes_used = wintypes.DWORD(0)

            res = psapi.EnumProcesses(cast(process_ids, wintypes.PDWORD), sizeof(process_ids), byref(bytes_used))
            if not res:
                return

            entries = int(bytes_used.value / sizeof(wintypes.DWORD))
            process_id_array_size += 512

        for process_id in process_ids[:entries]:
            process_handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, process_id)
            if process_handle:
                module = wintypes.HANDLE()
                needed_bytes = wintypes.LPDWORD()
                module_res = psapi.EnumProcessModules(
                    process_handle,
                    byref(module),
                    sizeof(module),
                    byref(needed_bytes)
                )
                if module_res:
                    length = 260
                    buffer = ctypes.create_unicode_buffer(length)
                    psapi.GetModuleBaseNameW(process_handle, module, buffer, length)
                    kernel32.CloseHandle(process_handle)
                    name = buffer.value
                    yield name.lower()
                    continue
                kernel32.CloseHandle(process_handle)

else:

    def list_process_names():
        """
        Stub for posix machines, unimplemented since it is not needed
        """

        return []
