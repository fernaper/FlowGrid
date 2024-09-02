from celery import Celery

from .config import Config


def make_celery(name: str = 'FlowGrid') -> Celery:
    celery = Celery(
        name,
        broker=Config.CELERY_BROKER_URL,
        backend=Config.CELERY_RESULT_BACKEND,
    )
    celery.conf.update(Config.CELERY_CONFIG)
    return celery


if __name__ == '__main__':
    celery = make_celery()
    # celery.worker_main(['worker', '--loglevel=info', '--concurrency=2'])
