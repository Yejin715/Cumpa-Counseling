from threading import Lock

class Singleton:
    """
    Thread‑safe Singleton base class.
    Subclasses should override _init() for one‑time initialization.
    """
    # The sole instance, shared across all threads
    _instance = None
    # A lock to prevent race conditions during first creation
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        # First check (without locking) for performance
        if cls._instance is None:
            # Acquire lock so only one thread can enter this block at a time
            with cls._lock:
                # Second check inside the lock to ensure no other thread created it
                if cls._instance is None:
                    # Actually create the instance
                    cls._instance = super().__new__(cls)
                    # Call one‑time initialization
                    cls._instance._init(*args, **kwargs)
        return cls._instance

    def _init(self, *args, **kwargs):
        """
        Override this in subclasses to perform initialization.
        This method is called exactly once, when the singleton is first created.
        """
        pass
