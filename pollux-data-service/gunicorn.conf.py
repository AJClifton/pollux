import os

from prometheus_client import multiprocess

bind = "0.0.0.0:8000"
workers = 4
worker_class = "sync"
timeout = 30
accesslog = "-"
errorlog = "-"
loglevel = "info"


def on_starting(server):
    """Clear stale prometheus_multiproc files on master startup.

    OOMKill / SIGKILL bypasses child_exit, leaving orphan *.db files that
    inflate scrape aggregation time across container lifetimes.
    """
    d = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if not d or not os.path.isdir(d):
        return
    for name in os.listdir(d):
        try:
            os.remove(os.path.join(d, name))
        except OSError:
            pass


def child_exit(server, worker):
    multiprocess.mark_process_dead(worker.pid)
