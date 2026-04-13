import threading
import time
import logging
from datetime import datetime
from typing import Optional, Dict


class SmartBatchEngine:
    """
    Debounce strategy for SMS processing.  When a new SMS arrives,
    wait for configurable delay to see if more arrive before
    running parser logic.  Reduces CPU usage during burst sync.
    """

    def __init__(self, process_callback, delay_seconds=60):
        self.process_callback = process_callback
        self.delay_seconds = delay_seconds
        self.timer = None
        self.batch = []
        self.lock = threading.Lock()
        self.instant_mode = False

    def add(self, item):
        """Add item to batch. If instant mode, process immediately."""
        with self.lock:
            self.batch.append(item)
            if self.instant_mode:
                self._flush()
            else:
                self._reset_timer()

    def _reset_timer(self):
        """Reset the debounce timer"""
        if self.timer:
            self.timer.cancel()
        self.timer = threading.Timer(self.delay_seconds, self._flush)
        self.timer.daemon = True
        self.timer.start()

    def _flush(self):
        """Process all batched items"""
        with self.lock:
            if self.batch:
                items = self.batch.copy()
                self.batch.clear()
        if items:
            try:
                self.process_callback(items)
            except Exception as e:
                logging.error(f"Batch processing error: {e}")

    def set_delay(self, seconds):
        """Update debounce delay"""
        self.delay_seconds = max(5, min(300, seconds))

    def set_instant(self, enabled):
        """Toggle instant processing mode"""
        self.instant_mode = enabled
