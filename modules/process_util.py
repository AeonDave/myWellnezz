import psutil


def kill_process(process_name: str) -> bool:
    system_process = list(
        filter(None, {p.name().split('.')[0].lower().strip() for p in psutil.process_iter()}))
    for proc in system_process:
        if proc in process_name:
            proc.kill()
            return True
    return False
