import logging
import os
import threading
import time

logger = logging.getLogger(__name__)

SPOF_REFRESH_INTERVAL = int(os.environ.get("SPOF_REFRESH_INTERVAL", 300))  # seconds

_started = False
_lock = threading.Lock()


def _run_spof_loop():
    """Background loop: apply SPOF detection every SPOF_REFRESH_INTERVAL seconds."""
    from assets.services.spof_detection import SpofDetector

    while True:
        try:
            result = SpofDetector().apply()
            logger.info(
                "SPOF auto-detection: %d SPOF found, %d changes applied.",
                result["total_spof"],
                result["total_changed"],
            )
        except Exception:
            logger.exception("SPOF auto-detection failed")
        time.sleep(SPOF_REFRESH_INTERVAL)


def start_spof_scheduler():
    """Start the background SPOF scheduler (once per process)."""
    global _started
    with _lock:
        if _started:
            return
        _started = True

    t = threading.Thread(target=_run_spof_loop, name="spof-scheduler", daemon=True)
    t.start()
    logger.info("SPOF scheduler started (interval=%ds).", SPOF_REFRESH_INTERVAL)
