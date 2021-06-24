## Celery

Supervisor config for Consoleme:

```ini
# Control Startup/Shutdown:
# sudo supervisorctl restart consolemeserver

[program:consolemeserver]
user=<CONSOLEME_USER>
autostart=true
autorestart=true
numprocs=1
directory=/apps/consoleme/
environment=
    CONSOLEME_CONFIG_ENTRYPOINT='YOUR_CONSOLEME_PLUGIN_ENTRYPOINT|default_config',
    PYTHONPATH='/apps/consoleme/',
    PATH='/apps/consoleme/bin:%(ENV_PATH)s',
    CONFIG_LOCATION='/path/to/your/config'
command=/apps/consoleme/bin/start_consoleme.sh "/apps/consoleme/bin/python -m consoleme.__main__"

; Causes supervisor to send the termination signal (SIGTERM) to the whole process group.
stopasgroup=true
```

`/apps/consoleme/bin/start_consoleme.sh` for us just initializes environmental variables that consoleme needs, netflix specifix ones

you'll want similar systemd/supervisor configurations for Celery scheduler and worker (commands incoming)

```bash
/apps/consoleme/bin/celery -A consoleme.celery_tasks.celery_tasks beat -l DEBUG --pidfile /tmp/celery.pid

/apps/consoleme/bin/celery -A consoleme.celery_tasks.celery_tasks worker -l DEBUG -E --pidfile /tmp/celery.pid --max-memory-per-child=1000000 --max-tasks-per-child 50 --soft-time-limit 3600 --concurrency=10 -O fair
```

(Only bring up one scheduler. You can bring up N workers and enable autoscaling if desired)

Tail Celery systemd logs:

```bash
journalctl -u celery -f
```

Tail ConsoleMe systemd logs:

```bash
journalctl -u consoleme -f
```

Debugging CloudInit:

```bash
vi /var/lib/cloud/instances/i-xxxxxxxx/scripts/part-001
```

To re-run the script you’ll need to clear the semaphores for the instance and kick it off the user scripts again with:

```bash
sudo rm -Rf /var/lib/cloud/instances/i-xxxxxxxx/sem
sudo /usr/bin/cloud-init single -n cc_scripts_user
```
