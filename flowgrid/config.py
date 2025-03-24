import os
from typing import List, Literal, TypedDict, Optional


class CeleryConfig(TypedDict):
    task_serializer: Literal['json', 'pickle', 'msgpack']
    result_serializer: Literal['json', 'pickle', 'msgpack']
    accept_content: List[Literal['json', 'pickle', 'msgpack']]
    timezone: str
    enable_utc: bool


VALID_SERIALIZERS: List[
    Literal['json', 'pickle', 'msgpack']
] = ['json', 'pickle', 'msgpack']


class Config:
    def __init__(
        self,
        celery_broker_url: Optional[str] = None,
        celery_result_backend: Optional[str] = None,
        celery_config: Optional[CeleryConfig] = None,
    ):
        """
        Initialize configuration with optional overrides.

        Args:
            celery_broker_url: Celery broker URL. Defaults to environment
                variable or 'amqp://guest:guest@localhost:5672//'.
            celery_result_backend: Celery result backend. Defaults to
                environment variable or 'redis://localhost:6380/0'.
            celery_config: Celery configuration dictionary. Defaults to
                environment variable or a dictionary with the following keys
                and values:
                {
                    'task_serializer': 'json',
                    'result_serializer': 'json',
                    'accept_content': ['json'],
                    'timezone': 'UTC',
                    'enable_utc': True
                }
        """
        # Global serializer from environment variable
        global_serializer = next(
            (
                serializer for serializer in VALID_SERIALIZERS
                if serializer == os.getenv('FLOWGRID_SERIALIZER', '')
            ),
            ''
        )

        # Celery Broker URL
        self.celery_broker_url = celery_broker_url or os.getenv(
            'FLOWGRID_CELERY_BROKER_URL',
            'amqp://guest:guest@localhost:5672//',
        )

        # Celery Result Backend
        self.celery_result_backend = celery_result_backend or os.getenv(
            'FLOWGRID_CELERY_RESULT_BACKEND',
            'redis://localhost:6380/0',
        )

        # Celery Configuration
        if celery_config is None:
            self.celery_config: CeleryConfig = {
                'task_serializer': next(
                    (
                        serializer for serializer in VALID_SERIALIZERS
                        if serializer == os.getenv('FLOWGRID_TASK_SERIALIZER', '')  # noqa E501
                    ),
                    global_serializer or 'json'
                ),
                'result_serializer': next(
                    (
                        serializer for serializer in VALID_SERIALIZERS
                        if serializer == os.getenv('FLOWGRID_RESULT_SERIALIZER', '')  # noqa E501
                    ),
                    global_serializer or 'json'
                ),
                'accept_content': [
                    next(
                        (
                            serializer for serializer in VALID_SERIALIZERS
                            if serializer == os.getenv('FLOWGRID_ACCEPT_CONTENT', '')  # noqa E501
                        ),
                        global_serializer or 'json'
                    )
                ],
                'timezone': os.getenv('FLOWGRID_TIMEZONE', 'UTC'),
                'enable_utc': os.getenv(
                    'FLOWGRID_ENABLE_UTC',
                    'True',
                ).lower() == 'true'
            }
        else:
            self.celery_config = celery_config

        self.validate()

    def validate(self) -> None:
        """
        Validate the configuration values.

        Raises:
            ValueError: If any configuration value is invalid.
        """
        # Validate Celery broker URL
        if not self.celery_broker_url.startswith(('amqp://', 'amqps://')):
            raise ValueError(
                f'Invalid Celery broker URL: {self.celery_broker_url}'
            )

        # Validate Celery result backend
        if not self.celery_result_backend.startswith(
            ('redis://', 'rediss://')
        ):
            raise ValueError(
                f'Invalid Celery result backend: {self.celery_result_backend}'
            )

        # Validate Celery config
        if self.celery_config['task_serializer'] not in VALID_SERIALIZERS:
            raise ValueError(
                f'Invalid task serializer: {self.celery_config["task_serializer"]}'  # noqa E501
            )

        if self.celery_config['result_serializer'] not in VALID_SERIALIZERS:
            raise ValueError(
                f'Invalid result serializer: {self.celery_config["result_serializer"]}'  # noqa E501
            )

        # Validate accept_content
        if not all(
            content in VALID_SERIALIZERS
            for content in self.celery_config['accept_content']
        ):
            raise ValueError(
                f'Invalid accept_content: {self.celery_config["accept_content"]}'  # noqa E501
            )

    @classmethod
    def from_env(cls) -> 'Config':
        """
        Create a configuration instance from environment variables.

        Returns:
            Config: A new configuration instance loaded from environment
            variables.
        """
        return cls()
