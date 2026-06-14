"""Useful utilities for managing sub-processes"""

import os
import errno


def is_process_running(pid: int) -> bool:
    """Is a process running?

    Args:
        pid (int): The process id to check

    Returns:
        bool: True if found
    """
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we don't have permission to signal it
        return True
    except OSError as e:
        if e.errno == errno.ESRCH:
            return False   # no such process
        if e.errno == errno.EPERM:
            return True    # exists, but you don't have permission to signal it
        raise e
    return True
