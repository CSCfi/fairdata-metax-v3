from metax_service.settings.components.base import env

ENABLE_BACKGROUND_TASKS = env.bool("ENABLE_BACKGROUND_TASKS", False)

# Django Q2 configuration
Q_CLUSTER = {
    "name": "metax-tasks",
    "orm": "default",  # Use default DB
    "workers": 2,  # Number of workers
    "queue_limit": 50,
    "timeout": 300,  # Task timeout in seconds
    "retry": 360,  # Time until task is retried, needs to be larger than timeout
    "max_attempts": 3,  # Number of attempts before giving up task
    "bulk": 1,  # Worker requests `bulk` tasks at once
    "poll": 5,  # Poll for tasks every `poll` seconds
    "recycle": 100,  # Number of tasks until worker is restarted
}
