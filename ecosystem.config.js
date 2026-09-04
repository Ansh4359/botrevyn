module.exports = {
  apps: [
    {
      name: 'botrevyn-web',
      script: './venv/bin/uvicorn',
      args: 'app.main:app --host 0.0.0.0 --port 8000',
      cwd: __dirname,
      interpreter: 'none',
      autorestart: true,
      restart_delay: 3000,
      max_memory_restart: '500M',
    },
    {
      name: 'botrevyn-worker',
      script: './venv/bin/celery',
      args: '-A app.tasks worker -l info --concurrency=1 --max-tasks-per-child=50',
      cwd: __dirname,
      interpreter: 'none',
      autorestart: true,
      restart_delay: 3000,
      max_memory_restart: '800M',
    },
  ],
};
