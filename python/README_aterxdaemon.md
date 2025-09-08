# Aterx Daemon

A service daemon that consolidates the functionality of `cleaner.sh`, `exporter.sh`, and `hashrate.sh` into a single Python application with an extensible task framework.

## Overview

The Aterx Daemon replaces the individual cronjobs that were running these three scripts every minute:
- **CleanerTask**: Handles share cleaning and reward splitting functionality (from `cleaner.sh`)
- **ExporterTask**: Handles stats export, log parsing, and file management (from `exporter.sh`)  
- **HashrateTask**: Handles hashrate calculations and Redis updates (from `hashrate.sh`)

## Features

- **Modular Design**: Easy to add new tasks by extending the `Task` base class
- **Configurable**: Uses the same configuration file as other p2pooler components
- **Robust**: Includes error handling, logging, and graceful shutdown
- **Flexible**: Command-line options for testing, debugging, and customization
- **Production Ready**: Includes systemd service file and startup scripts

## Requirements

- Python 3.10+
- Redis-stack-server (for data storage) without stack-server we're missing the JSON and Search modules.
- Required Python packages: `redis`, `monero` (automatically installed)

## Installation

1. The daemon is already included in the p2pooler repository at `python/aterxdaemon.py`
2. Install Python dependencies:
   ```bash
   pip install redis monero
   ```
3. Ensure your p2pooler configuration file exists at `~/.config/p2pooler-py.json`

## Usage

### Command Line Options

```bash
# Show help
python3 aterxdaemon.py --help

# Run with default settings (60-second interval)
python3 aterxdaemon.py

# Run with custom interval and debug logging
python3 aterxdaemon.py --interval 30 --log-level DEBUG

# Test configuration and run one cycle
python3 aterxdaemon.py --test

# Run as background daemon
python3 aterxdaemon.py --daemon

# Disable specific tasks
python3 aterxdaemon.py --disable-cleaner --disable-exporter
```

### Configuration

The daemon uses the same configuration file as other p2pooler components (`~/.config/p2pooler-py.json`). Required configuration keys:

```json
{
    "monero_rpc": "http://localhost:18081",
    "monero_ip": "localhost",
    "wallet_rpc": "http://localhost:18082", 
    "receiver_port": 8080,
    "redis_port": 6379,
    "v1_template_html": "v1_template.html",
    "p2pool_stats": "/path/to/p2pool/stats",
    "p2pooler_rpc": "http://localhost:8080",
    "p2pooler_token": "your-token",
    "stats_dir": "/path/to/stats/directory",
    "site_ip": "your.site.ip",
    "p2pool_log": "/path/to/p2pool.log"
}
```

### Using the Startup Script

A convenience script is provided for managing the daemon:

```bash
# Start the daemon
./start_aterxdaemon.sh start

# Stop the daemon
./start_aterxdaemon.sh stop

# Restart the daemon
./start_aterxdaemon.sh restart

# Check status
./start_aterxdaemon.sh status

# Test configuration
./start_aterxdaemon.sh test
```

### Using Systemd (Production)

1. Copy the service file:
   ```bash
   sudo cp aterxdaemon.service /etc/systemd/system/
   ```

2. Update the service file paths to match your installation

3. Enable and start the service:
   ```bash
   sudo systemctl enable aterxdaemon
   sudo systemctl start aterxdaemon
   ```

4. Check status:
   ```bash
   sudo systemctl status aterxdaemon
   ```

## Task Details

### CleanerTask
- Cleans old shares from Redis (>18 hours old)
- Monitors memory usage and provides statistics
- Checks for blocks needing reward splitting
- Logs all operations with timestamps

### ExporterTask
- Removes old stats files (>910 minutes)
- Downloads latest stats from configured site
- Removes broken stats files (<300 bytes)
- Sends status commands to p2pool console
- Parses p2pool log files for share data

### HashrateTask
- Calculates hashrates for different time windows
- Updates Redis with hashrate data for all users
- Maintains super user aggregate hashrates
- Cleans up hashrate keys for inactive users

## Adding New Tasks

To add a new task, extend the `Task` base class:

```python
class MyNewTask(Task):
    def __init__(self, config: dict, logger: logging.Logger):
        super().__init__("mynew", config, logger)
    
    async def execute(self) -> None:
        if not self.enabled:
            return
        
        self.logger.info("Running my new task")
        # Your task logic here
        self.logger.info("My new task completed")
```

Then add it to the daemon's task list in the `_initialize_tasks` method.

## Logging

The daemon provides structured logging with different levels:
- **DEBUG**: Detailed information for debugging
- **INFO**: General operational messages (default)
- **WARNING**: Warning messages for non-critical issues
- **ERROR**: Error messages for failures

In daemon mode, logs go to syslog. In interactive mode, logs go to stdout.

## Migration from Cron Jobs

To migrate from the existing cron-based setup:

1. Remove the existing cron entries for `cleaner.sh`, `exporter.sh`, and `hashrate.sh`
2. Start the aterxdaemon using one of the methods above
3. Monitor logs to ensure all tasks are running correctly

The daemon preserves all the functionality of the original scripts while providing better error handling, logging, and management capabilities.

## Troubleshooting

### Common Issues

1. **Redis Connection Errors**: Ensure Redis is running and accessible on the configured port
2. **Permission Errors**: Ensure the daemon has read/write access to log directories and stats directories
3. **Configuration Errors**: Use `--test` mode to validate configuration before running

### Debugging

Use debug logging to troubleshoot issues:
```bash
python3 aterxdaemon.py --log-level DEBUG --test
```

Check the logs for detailed error messages and execution flow.
