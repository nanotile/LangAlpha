"""
Server script
"""

import argparse
import logging
import os
import uvicorn

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run the server")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (default: True except on Windows)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.getenv("UVICORN_WORKERS", "1")),
        help="Number of uvicorn worker processes (default: 1, or UVICORN_WORKERS env var). "
             "Values >1 require that in-process singletons (WorkspaceManager, "
             "BackgroundTaskManager, SessionService) have their shared state moved to "
             "Redis. Until that refactor, use 1 for correctness.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Log level (default: info)",
    )

    args = parser.parse_args()

    # Configure SSE event logger independently
    # This allows viewing ONLY SSE events by setting SSE_EVENT_LOG_LEVEL=info
    # and server --log-level=error
    sse_event_log_level = os.getenv("SSE_EVENT_LOG_LEVEL", "info").upper()
    sse_logger = logging.getLogger("sse_events")
    sse_logger.setLevel(getattr(logging, sse_event_log_level))
    # Add dedicated handler so SSE logs output independently of root logger level
    sse_handler = logging.StreamHandler()
    sse_handler.setLevel(getattr(logging, sse_event_log_level))
    sse_handler.setFormatter(logging.Formatter("%(message)s"))
    sse_logger.addHandler(sse_handler)
    # Prevent duplicate logs by not propagating to root logger
    sse_logger.propagate = False


    # Determine reload setting
    reload = False
    if args.reload:
        reload = True

    workers = args.workers
    if reload and workers > 1:
        logger.warning("--reload is incompatible with --workers > 1, forcing workers=1")
        workers = 1

    if workers == 1:
        logger.info(
            "Running with 1 worker. For production throughput, set --workers or "
            "UVICORN_WORKERS (requires singleton state refactor — see EVALUATE_REPORT.md)."
        )

    try:
        logger.info(f"Starting server on {args.host}:{args.port} (workers={workers})")
        uvicorn.run(
            "src.server.app:app",
            host=args.host,
            port=args.port,
            workers=workers,
            reload=reload,
            log_level=args.log_level,
            timeout_keep_alive=300,  # 5 minutes - for long-running workflows
            timeout_graceful_shutdown=60,  # 60 seconds for graceful shutdown
        )
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        exit(1)
