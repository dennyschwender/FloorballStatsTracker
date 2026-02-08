"""
File operations with cross-platform locking and atomic writes
"""
import os
import json
import tempfile
import platform

# Platform-specific imports for file locking
if platform.system() == 'Windows':
    import msvcrt
else:
    import fcntl


def _acquire_file_lock(file_handle, exclusive=True):
    """Acquire a file lock (cross-platform)"""
    if platform.system() == 'Windows':
        # Windows file locking
        mode = msvcrt.LK_NBLCK if exclusive else msvcrt.LK_NBRLCK
        max_retries = 10
        for _ in range(max_retries):
            try:
                msvcrt.locking(file_handle.fileno(), mode, 1)
                return True
            except OSError:
                import time
                time.sleep(0.1)
        return False
    else:
        # Unix file locking
        operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        try:
            fcntl.flock(file_handle.fileno(), operation | fcntl.LOCK_NB)
            return True
        except IOError:
            # Try with blocking
            fcntl.flock(file_handle.fileno(), operation)
            return True


def _release_file_lock(file_handle):
    """Release a file lock (cross-platform)"""
    if platform.system() == 'Windows':
        try:
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
    else:
        try:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
        except IOError:
            pass


def safe_write_json(filepath, data):
    """Atomically write JSON data to a file with proper locking"""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
    
    # Write to a temporary file first
    temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(filepath) or '.', suffix='.tmp')
    
    try:
        with os.fdopen(temp_fd, 'w') as temp_file:
            json.dump(data, temp_file, indent=2)
        
        # Atomically replace the original file
        # On Windows, we need to remove the target first
        if platform.system() == 'Windows' and os.path.exists(filepath):
            os.replace(temp_path, filepath)
        else:
            os.rename(temp_path, filepath)
        
        return True
    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise e


def safe_read_json(filepath):
    """Read JSON data from a file with proper locking"""
    try:
        with open(filepath, 'r') as f:
            # Acquire shared lock for reading
            _acquire_file_lock(f, exclusive=False)
            try:
                data = json.load(f)
            finally:
                _release_file_lock(f)
            return data
    except FileNotFoundError:
        return None
    except Exception:
        return None
