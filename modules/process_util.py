import psutil


def check_name(proc_name: str, confront: str) -> bool:
    if proc_name == confront:
        return True
    parts = proc_name.split('.')
    return '.'.join(parts[:-1]) == confront if len(parts) > 1 else False


def kill_process_byname(process_name: str):
    process_name = process_name.lower().strip()
    processes = list(filter(lambda p: check_name(p.name().lower().strip(), process_name), psutil.process_iter()))
    for proc in processes:
        proc.kill()


def kill_process_bypid(process_pid: int):
    processes = list(filter(lambda p: p.pid == process_pid, psutil.process_iter()))
    for proc in processes:
        proc.kill()
