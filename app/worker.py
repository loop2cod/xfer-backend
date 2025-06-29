from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "xfer_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.blockchain", "app.tasks.notifications"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Configure periodic tasks
celery_app.conf.beat_schedule = {
    'monitor-blockchain-transactions': {
        'task': 'app.tasks.blockchain.monitor_pending_transactions',
        'schedule': 60.0,  # Run every minute
    },
    'cleanup-expired-transfers': {
        'task': 'app.tasks.blockchain.cleanup_expired_transfers',
        'schedule': 300.0,  # Run every 5 minutes
    },
    'update-wallet-balances': {
        'task': 'app.tasks.blockchain.update_wallet_balances',
        'schedule': 180.0,  # Run every 3 minutes
    },
}

if __name__ == "__main__":
    celery_app.start()