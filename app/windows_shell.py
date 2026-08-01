from __future__ import annotations

import ctypes
import sys
from pathlib import Path


def _open_folder_and_select_item(file_path: Path) -> None:
    """通过 Windows Shell 原生接口打开父目录并选中文件。"""
    if sys.platform != "win32":
        raise OSError("精确定位文件仅支持 Windows。")

    ole32 = ctypes.WinDLL("ole32", use_last_error=True)
    ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    ole32.CoInitializeEx.restype = ctypes.c_long
    ole32.CoUninitialize.argtypes = []
    ole32.CoUninitialize.restype = None

    # SHOpenFolderAndSelectItems 依赖调用线程已初始化 COM。
    com_result = ole32.CoInitializeEx(None, 2)  # COINIT_APARTMENTTHREADED
    com_initialized_here = com_result in (0, 1)  # S_OK / S_FALSE
    if com_result not in (0, 1, -2147417850):  # RPC_E_CHANGED_MODE 可继续使用现有模型
        raise OSError(com_result, "Windows COM 初始化失败，无法定位文件。")

    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    shell32.ILCreateFromPathW.argtypes = [ctypes.c_wchar_p]
    shell32.ILCreateFromPathW.restype = ctypes.c_void_p
    shell32.SHOpenFolderAndSelectItems.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_void_p,
        ctypes.c_ulong,
    ]
    shell32.SHOpenFolderAndSelectItems.restype = ctypes.c_long
    shell32.ILFree.argtypes = [ctypes.c_void_p]
    shell32.ILFree.restype = None

    try:
        item_id_list = shell32.ILCreateFromPathW(str(file_path))
        if not item_id_list:
            raise OSError(ctypes.get_last_error(), f"Windows 无法识别文件路径：{file_path}")
        try:
            result = shell32.SHOpenFolderAndSelectItems(item_id_list, 0, None, 0)
            if result != 0:
                raise OSError(result, f"Windows 资源管理器无法定位文件：{file_path}")
        finally:
            shell32.ILFree(item_id_list)
    finally:
        if com_initialized_here:
            ole32.CoUninitialize()


def reveal_file_in_explorer(file_path: Path) -> Path:
    """打开文件所在目录，并在资源管理器中选中该文件。"""
    resolved = file_path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"文件不存在：{resolved}")
    _open_folder_and_select_item(resolved)
    return resolved
