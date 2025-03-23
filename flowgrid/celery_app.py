from celery import Celery

from .config import Config


def make_celery(name: str = 'FlowGrid') -> Celery:
    config = Config.from_env()
    celery = Celery(
        name,
        broker=config.celery_broker_url,
        backend=config.celery_result_backend,
    )
    celery.conf.update(config.celery_config)
    return celery


if __name__ == '__main__':
    celery = make_celery()
    # celery.worker_main(['worker', '--loglevel=info', '--concurrency=2'])
