"""Keep the system awake while the app waits for booking windows.

Uses ``SetThreadExecutionState`` on Windows: the process declares "system in
use" and Windows suspends sleep for as long as it runs. Unlike the v1 approach
(random mouse jiggling) it never touches the user's cursor.
"""

import ctypes
import sys
import threading

_ES_CONTINUOUS = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001

_REFRESH_SECONDS = 60

_stop: threading.Event | None = None
_thread: threading.Thread | None = None


def _keep_awake(stop: threading.Event) -> None:
    set_state = ctypes.windll.kernel32.SetThreadExecutionState
    set_state(_ES_CONTINUOUS | _ES_SYSTEM_REQUIRED)
    while not stop.wait(_REFRESH_SECONDS):
        set_state(_ES_CONTINUOUS | _ES_SYSTEM_REQUIRED)
    set_state(_ES_CONTINUOUS)


def start_keep_awake() -> None:
    global _stop, _thread
    if sys.platform != 'win32' or (_thread is not None and _thread.is_alive()):
        return
    _stop = threading.Event()
    _thread = threading.Thread(target=_keep_awake, args=(_stop,), daemon=True, name='keep-awake')
    _thread.start()
