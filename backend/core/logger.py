import logging
import sys
import os

# Ensure `log` exists even if _build_logger fails during import
log = None


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
    log_dir = os.getenv("LOG_DIR", "logs")
    log_path = os.path.join(log_dir, "app.log")
    try:
        try:
            os.makedirs(log_dir, exist_ok=True)
        except OSError:
            # Directory may be on a read-only or full filesystem; fall back to console-only
            logger.warning(f"Could not create log dir '{log_dir}' — falling back to console only")
            return logger

        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)             # ✅ file captures all
        fh.setFormatter(logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(fh)
    except Exception as e:
        logger.warning(f"Unable to configure file logger ({e}) — continuing with console only")

    return logger


try:
    log = _build_logger()
except Exception:
    # Fallback minimal logger to avoid import-time failures in other modules
    fallback = logging.getLogger("fwg_ai_os")
    if not fallback.handlers:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        fallback.addHandler(ch)
    fallback.setLevel(logging.INFO)
    log = fallback
