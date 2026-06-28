import logging
import sys


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("fwg_ai_os")   # ✅ named, not root

    if logger.handlers:                        # ✅ no duplicate on reload
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False                   # ✅ block root logger spam

    # ── Console ─────────────────────────────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)             # ✅ Dev: INFO default
    console.setFormatter(logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(console)

    # ── File ────────────────────────────────────────────────────────
    try:
        fh = logging.FileHandler("logs/app.log", encoding="utf-8")
        fh.setLevel(logging.DEBUG)             # ✅ file captures all
        fh.setFormatter(logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(fh)
    except FileNotFoundError:
        logger.warning("logs/ not found — run: mkdir -p logs")

    return logger


log = _build_logger()
