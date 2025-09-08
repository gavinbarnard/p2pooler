#!/usr/bin/env python3
# * p2pooler
# * Copyright 2022      grb         <https://github.com/gavinbarnard>
# *
# *   This program is free software: you can redistribute it and/or modify
# *   it under the terms of the GNU General Public License as published by
# *   the Free Software Foundation, either version 3 of the License, or
# *   (at your option) any later version.
# *
# *   This program is distributed in the hope that it will be useful,
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *   GNU General Public License for more details.
# *
# *   You should have received a copy of the GNU General Public License
# *   along with this program. If not, see <http://www.gnu.org/licenses/>.
# */

"""
aterxdaemon.py - A service daemon that consolidates the functionality of 
cleaner.sh, exporter.sh, and hashrate.sh into a single Python application 
with an extensible task framework.
"""

import asyncio
import logging
import signal
import sys
import os
import json
import subprocess
import time
import glob
import argparse
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import urllib.request
import urllib.error
import socket
import redis
from math import floor

# Import existing utility modules
from util.config import parse_config


class Task(ABC):
    """Abstract base class for daemon tasks"""
    
    def __init__(self, name: str, config: dict, logger: logging.Logger):
        self.name = name
        self.config = config
        self.logger = logger
        self.enabled = True
    
    @abstractmethod
    async def execute(self) -> None:
        """Execute the task"""
        pass
    
    def disable(self):
        """Disable this task"""
        self.enabled = False
    
    def enable(self):
        """Enable this task"""
        self.enabled = True


class CleanerTask(Task):
    """Task that handles cleaning shares and reward splitting functionality"""
    
    def __init__(self, config: dict, logger: logging.Logger):
        super().__init__("cleaner", config, logger)
        self.redis_client = redis.Redis(port=config.get('redis_port', 6379))
        
    async def execute(self) -> None:
        """Execute cleaner functionality"""
        if not self.enabled:
            return
            
        self.logger.info("Starting cleaner task")
        
        # Run the cleaning functionality (equivalent to running cleaner.py)
        await self._run_cleaner()
        
        # Handle reward processing (equivalent to curl + reward_splitter logic)
        await self._handle_rewards()
        
        self.logger.info("Cleaner task completed")
    
    async def _run_cleaner(self):
        """Run the share cleaning logic from cleaner.py"""
        try:
            total_mem_pre_clean = 0
            total_rmem_pre_clean = 0
            total_mem_post_clean = 0
            total_rmem_post_clean = 0
            
            resp = self.redis_client.keys("s_*")
            for key in resp:
                s_count = self.redis_client.json().arrlen(key)
                memory = self.redis_client.json().debug("MEMORY", key)
                raw_memory = self.redis_client.memory_usage(key)
                
                self.logger.debug(f"before user: {str(key[2:], 'utf-8')} shares: {s_count} memory: j{self._fmt_memory(memory)} r{self._fmt_memory(raw_memory)}")
                
                total_mem_pre_clean += memory
                total_rmem_pre_clean += raw_memory
                
                ts_list = self.redis_client.json().get(key, "$..timestamp")
                ts = int(time.time() * 1000)
                last_found = -1
                
                for i in range(len(ts_list)):
                    if ts - ts_list[i] > 64836000:  # ~18 hours
                        last_found = i
                    else:
                        break
                
                if last_found == -1:
                    self.logger.debug("no shares to kill")
                else:
                    self.logger.debug(f"keeping shares {last_found + 1} to {s_count - 1}")
                    self.redis_client.json().arrtrim(key, "$", last_found + 1, s_count - 1)
                
                s_count = self.redis_client.json().arrlen(key)
                if s_count == 0:
                    self.redis_client.json().forget(key)
                    self.logger.debug(f"dropping {str(key, 'utf-8')} key because no shares remain")
                else:
                    last_ts = self.redis_client.json().get(key, f"$[{s_count - 1}].timestamp")
                    memory = self.redis_client.json().debug("MEMORY", key)
                    raw_memory = self.redis_client.memory_usage(key)
                    total_mem_post_clean += memory
                    total_rmem_post_clean += raw_memory
                    self.logger.debug(f"after user: {str(key[2:], 'utf-8')} shares: {s_count} last share at: {last_ts} memory: j{self._fmt_memory(memory)} r{self._fmt_memory(raw_memory)}")
            
            self.logger.info(f"total memory before/after clean: j{self._fmt_memory(total_mem_pre_clean)} / {self._fmt_memory(total_mem_post_clean)} - r{self._fmt_memory(total_rmem_pre_clean)} / {self._fmt_memory(total_rmem_post_clean)}")
            
            mstats = self.redis_client.memory_stats()
            self.logger.info(f"peak alloc: {self._fmt_memory(mstats['peak.allocated'])}")
            self.logger.info(f"total allocated: {self._fmt_memory(mstats['total.allocated'])}")
            self.logger.info(f"key count: {mstats['keys.count']}")
            self.logger.info(f"bytes per key: {self._fmt_memory(mstats['keys.bytes-per-key'])}")
            self.logger.info(f"dataset size: {self._fmt_memory(mstats['dataset.bytes'])}")
            
        except Exception as e:
            self.logger.error(f"Error in cleaner task: {e}")
    
    async def _handle_rewards(self):
        """Handle reward splitting logic"""
        try:
            site_ip = self.config.get('site_ip')
            if not site_ip:
                self.logger.warning("site_ip not configured, skipping reward processing")
                return
            
            # Check for blocks needing rewards
            url = f"http://{site_ip}/1/needreward"
            req = urllib.request.Request(url)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                count = len(data) if data else 0
                
                if count != 0:
                    self.logger.info(f"{count} blocks found that need to be split")
                    # Note: reward_splitter.py is commented out in original script
                    # Uncomment the next line to enable reward splitting
                    # await self._run_reward_splitter()
                else:
                    self.logger.info("no blocks found that need to be split")
                    
        except urllib.error.URLError as e:
            self.logger.error(f"Error checking for rewards: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in reward handling: {e}")
    
    async def _run_reward_splitter(self):
        """Run reward splitter functionality (currently disabled)"""
        # This would implement the reward_splitter.py functionality
        # Left as placeholder for future implementation
        pass
    
    def _fmt_memory(self, memory):
        """Format memory size for display"""
        size_dict = ['b', 'kb', 'mb', 'gb', 'tb']
        count = 0
        while memory > 10240:
            memory = memory / 1024
            count += 1
            if count == 4:
                break
        return f"{round(memory, 2)} {size_dict[count]}"


class ExporterTask(Task):
    """Task that handles stats export and log parsing functionality"""
    
    def __init__(self, config: dict, logger: logging.Logger):
        super().__init__("exporter", config, logger)
        
    async def execute(self) -> None:
        """Execute exporter functionality"""
        if not self.enabled:
            return
            
        self.logger.info("Starting exporter task")
        
        # Clean up old stats files
        await self._cleanup_old_stats()
        
        # Download latest stats
        await self._download_latest_stats()
        
        # Clean up broken stats files
        await self._cleanup_broken_stats()
        
        # Run p2pool console status
        await self._run_p2pool_console_status()
        
        # Parse p2pool log for share information
        await self._parse_p2pool_log()
        
        self.logger.info("Exporter task completed")
    
    async def _cleanup_old_stats(self):
        """Remove JSON files older than 910 minutes"""
        try:
            stats_dir = self.config.get('stats_dir')
            if not stats_dir:
                self.logger.warning("stats_dir not configured")
                return
            
            # Find and remove old JSON files
            old_time = time.time() - (910 * 60)  # 910 minutes ago
            pattern = os.path.join(stats_dir, "*.json")
            
            removed_count = 0
            for filepath in glob.glob(pattern):
                if os.path.getmtime(filepath) < old_time:
                    os.remove(filepath)
                    removed_count += 1
            
            if removed_count > 0:
                self.logger.debug(f"Removed {removed_count} old stats files")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up old stats: {e}")
    
    async def _download_latest_stats(self):
        """Download latest stats from site"""
        try:
            stats_dir = self.config.get('stats_dir')
            site_ip = self.config.get('site_ip')
            
            if not stats_dir or not site_ip:
                self.logger.warning("stats_dir or site_ip not configured")
                return
            
            url = f"http://{site_ip}/1/stats"
            timestamp = datetime.now(timezone.utc).isoformat()
            filename = f"latest-{timestamp}.json"
            filepath = os.path.join(stats_dir, filename)
            
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read()
                
                with open(filepath, 'wb') as f:
                    f.write(data)
                
                self.logger.debug(f"Downloaded stats to {filename}")
                
        except urllib.error.URLError as e:
            self.logger.error(f"Error downloading stats: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error downloading stats: {e}")
    
    async def _cleanup_broken_stats(self):
        """Remove broken stats files (< 300 bytes)"""
        try:
            stats_dir = self.config.get('stats_dir')
            if not stats_dir:
                return
            
            pattern = os.path.join(stats_dir, "*.json")
            removed_count = 0
            
            for filepath in glob.glob(pattern):
                if os.path.getsize(filepath) < 300:
                    os.remove(filepath)
                    removed_count += 1
            
            if removed_count > 0:
                self.logger.debug(f"Removed {removed_count} broken stats files")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up broken stats: {e}")
    
    async def _run_p2pool_console_status(self):
        """Run p2pool console status command"""
        try:
            p2pool_stats_dir = self.config.get('p2pool_stats')
            if not p2pool_stats_dir:
                self.logger.warning("p2pool_stats not configured")
                return
            
            console_file = os.path.join(p2pool_stats_dir, 'local', 'console')
            if not os.path.exists(console_file):
                self.logger.warning(f"Console file not found: {console_file}")
                return
            
            with open(console_file, 'r') as f:
                data = json.load(f)
            
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('127.0.0.1', data['tcp_port']))
            
            command = data['cookie'] + "status\n"
            s.sendall(command.encode('utf-8'))
            s.close()
            
            self.logger.debug("Sent p2pool console status command")
            
        except Exception as e:
            self.logger.error(f"Error running p2pool console status: {e}")
    
    async def _parse_p2pool_log(self):
        """Parse p2pool log file for share information"""
        try:
            stats_dir = self.config.get('stats_dir')
            logfile = self.config.get('p2pool_log')
            
            if not stats_dir or not logfile:
                self.logger.warning("stats_dir or p2pool_log not configured")
                return
            
            if not os.path.exists(logfile):
                self.logger.warning(f"P2Pool log file not found: {logfile}")
                return
            
            # Parse shares data
            shares_file = os.path.join(stats_dir, 'shares.json')
            shares_window_file = os.path.join(stats_dir, 'shares_window')
            
            # Extract shares information using grep equivalent
            shares_data = await self._extract_shares_data(logfile)
            if shares_data:
                with open(shares_file, 'w') as f:
                    f.write(shares_data)
                self.logger.debug("Updated shares.json")
            
            # Extract shares window information
            shares_window = await self._extract_shares_window(logfile)
            if shares_window:
                with open(shares_window_file, 'w') as f:
                    f.write(shares_window)
                self.logger.debug("Updated shares_window")
                
        except Exception as e:
            self.logger.error(f"Error parsing p2pool log: {e}")
    
    async def _extract_shares_data(self, logfile: str) -> Optional[str]:
        """Extract shares data from log file"""
        try:
            # Equivalent to: grep "Your shares               = " $logfile | awk '{print "{\"shares\": " $4 ",\"uncles\": " substr($6,3) ",\"orphans\": " $8"}"'} | tail -1
            with open(logfile, 'r') as f:
                lines = f.readlines()
            
            for line in reversed(lines):
                if "Your shares               = " in line:
                    parts = line.strip().split()
                    if len(parts) >= 8:
                        shares = parts[3]
                        uncles = parts[5][2:]  # Remove first 2 characters
                        orphans = parts[7]
                        return f'{{"shares": {shares}, "uncles": {uncles}, "orphans": {orphans}}}'
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting shares data: {e}")
            return None
    
    async def _extract_shares_window(self, logfile: str) -> Optional[str]:
        """Extract shares window from log file"""
        try:
            # Equivalent to: grep "Your shares po" $logfile | awk '{print $5}' | tail -1
            with open(logfile, 'r') as f:
                lines = f.readlines()
            
            for line in reversed(lines):
                if "Your shares po" in line:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        return parts[4]
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting shares window: {e}")
            return None


class HashrateTask(Task):
    """Task that handles hashrate calculation functionality"""
    
    def __init__(self, config: dict, logger: logging.Logger):
        super().__init__("hashrate", config, logger)
        self.redis_client = redis.Redis(port=config.get('redis_port', 6379))
        
    async def execute(self) -> None:
        """Execute hashrate functionality"""
        if not self.enabled:
            return
            
        self.logger.info("Starting hashrate task")
        
        try:
            start = floor(time.time() * 1000)
            
            keys = self.redis_client.keys("s_*")
            super_overall_hr = {
                120: 0, 300: 0, 600: 0, 1800: 0,
                3600: 0, 7200: 0, 21600: 0, 64800: 0
            }
            
            for key in keys:
                userkey = str(key[2:], 'utf-8')
                shares = self._get_shares(userkey)
                if shares:
                    overall_hr = self._determine_hr(shares, start)
                    self.redis_client.json().set(f"h_{userkey}", ".", overall_hr)
                    for k in overall_hr.keys():
                        super_overall_hr[k] += overall_hr[k]
            
            # Clean up hashrate keys for users with no shares
            h_keys = self.redis_client.keys("h_*")
            for key in h_keys:
                userkey = str(key[2:], 'utf-8')
                if not self._get_shares(userkey) and userkey != "super":
                    self.redis_client.delete(key)
            
            # Set super hashrate
            self.redis_client.json().set("h_super", ".", super_overall_hr)
            
            self.logger.info("Hashrate task completed")
            
        except Exception as e:
            self.logger.error(f"Error in hashrate task: {e}")
    
    def _get_shares(self, user: str):
        """Get shares for a user"""
        shares = None
        resp = self.redis_client.keys(f"s_{user}")
        for key in resp:
            shares = self.redis_client.json().get(key)
        return shares
    
    def _determine_hr(self, shares, start_time):
        """Calculate hashrate for different time buckets"""
        buckets = {
            120: 0, 300: 0, 600: 0, 1800: 0,
            3600: 0, 7200: 0, 21600: 0, 64800: 0
        }
        hr = {}
        
        for i in reversed(range(len(shares))):
            tdiff = (start_time - shares[i]['timestamp']) / 1000
            for k in buckets.keys():
                if tdiff < k:
                    buckets[k] += shares[i]['diff']
        
        for k in buckets.keys():
            hr[k] = floor(buckets[k] / k)
        
        return hr


class AterxDaemon:
    """Main daemon class that manages tasks and scheduling"""
    
    def __init__(self, config_file: Optional[str] = None, log_level: str = "INFO", 
                 task_interval: int = 60, daemon_mode: bool = False):
        self.config_file = config_file or self._get_default_config_file()
        self.config = parse_config(self.config_file)
        self.log_level = log_level
        self.daemon_mode = daemon_mode
        self.logger = self._setup_logging()
        self.tasks: List[Task] = []
        self.running = False
        self.task_interval = task_interval  # Run tasks every N seconds
        
        # Initialize tasks
        self._initialize_tasks()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _get_default_config_file(self) -> str:
        """Get default config file path"""
        return os.path.join(os.environ['HOME'], '.config', 'p2pooler-py.json')
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('aterxdaemon')
        logger.setLevel(getattr(logging, self.log_level.upper()))
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        if self.daemon_mode:
            # In daemon mode, log to syslog or file
            try:
                from logging.handlers import SysLogHandler
                handler = SysLogHandler(address='/dev/log')
                formatter = logging.Formatter(
                    'aterxdaemon[%(process)d]: %(levelname)s - %(message)s'
                )
            except Exception:
                # Fallback to file logging
                log_file = '/var/log/aterxdaemon.log'
                handler = logging.FileHandler(log_file)
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
        else:
            # Console logging for non-daemon mode
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        handler.setLevel(getattr(logging, self.log_level.upper()))
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _initialize_tasks(self):
        """Initialize all tasks"""
        self.tasks = [
            CleanerTask(self.config, self.logger),
            ExporterTask(self.config, self.logger),
            HashrateTask(self.config, self.logger)
        ]
        
        self.logger.info(f"Initialized {len(self.tasks)} tasks")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        self.running = False
    
    def add_task(self, task: Task):
        """Add a new task to the daemon"""
        self.tasks.append(task)
        self.logger.info(f"Added task: {task.name}")
    
    def remove_task(self, task_name: str):
        """Remove a task by name"""
        self.tasks = [t for t in self.tasks if t.name != task_name]
        self.logger.info(f"Removed task: {task_name}")
    
    async def _run_tasks(self):
        """Run all enabled tasks"""
        tasks_to_run = [task.execute() for task in self.tasks if task.enabled]
        
        if tasks_to_run:
            await asyncio.gather(*tasks_to_run, return_exceptions=True)
    
    async def run(self):
        """Main daemon loop"""
        self.running = True
        self.logger.info("Aterx daemon starting...")
        self.logger.info(f"Running {len(self.tasks)} tasks every {self.task_interval} seconds")
        
        while self.running:
            try:
                cycle_start = time.time()
                
                # Run all tasks
                await self._run_tasks()
                
                # Calculate sleep time to maintain interval
                cycle_duration = time.time() - cycle_start
                sleep_time = max(0, self.task_interval - cycle_duration)
                
                if sleep_time > 0:
                    self.logger.debug(f"Task cycle completed in {cycle_duration:.2f}s, sleeping for {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)
                else:
                    self.logger.warning(f"Task cycle took {cycle_duration:.2f}s, longer than interval {self.task_interval}s")
                
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(1)  # Brief pause before retrying
        
        self.logger.info("Aterx daemon stopped")


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Aterx daemon - Consolidates cleaner, exporter, and hashrate tasks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Run with default settings
  %(prog)s --config /path/to/config.json     # Use custom config file
  %(prog)s --interval 30 --log-level DEBUG   # Run every 30 seconds with debug logging
  %(prog)s --daemon                          # Run as background daemon
  %(prog)s --test                            # Test configuration and tasks, then exit
        """
    )
    
    parser.add_argument(
        '-c', '--config',
        default=None,
        help='Configuration file path (default: ~/.config/p2pooler-py.json)'
    )
    
    parser.add_argument(
        '-i', '--interval',
        type=int,
        default=60,
        help='Task execution interval in seconds (default: 60)'
    )
    
    parser.add_argument(
        '-l', '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '-d', '--daemon',
        action='store_true',
        help='Run as background daemon'
    )
    
    parser.add_argument(
        '-t', '--test',
        action='store_true',
        help='Test configuration and run one cycle of tasks, then exit'
    )
    
    parser.add_argument(
        '--disable-cleaner',
        action='store_true',
        help='Disable the cleaner task'
    )
    
    parser.add_argument(
        '--disable-exporter',
        action='store_true',
        help='Disable the exporter task'
    )
    
    parser.add_argument(
        '--disable-hashrate',
        action='store_true',
        help='Disable the hashrate task'
    )
    
    return parser.parse_args()


async def main():
    """Main entry point"""
    args = parse_args()
    
    try:
        daemon = AterxDaemon(
            config_file=args.config,
            log_level=args.log_level,
            task_interval=args.interval,
            daemon_mode=args.daemon
        )
        
        # Disable tasks based on command line args
        if args.disable_cleaner:
            for task in daemon.tasks:
                if task.name == 'cleaner':
                    task.disable()
                    daemon.logger.info("Cleaner task disabled")
        
        if args.disable_exporter:
            for task in daemon.tasks:
                if task.name == 'exporter':
                    task.disable()
                    daemon.logger.info("Exporter task disabled")
        
        if args.disable_hashrate:
            for task in daemon.tasks:
                if task.name == 'hashrate':
                    task.disable()
                    daemon.logger.info("Hashrate task disabled")
        
        if args.test:
            # Test mode - run one cycle and exit
            daemon.logger.info("Running in test mode...")
            await daemon._run_tasks()
            daemon.logger.info("Test completed successfully")
            return
        
        # Run the daemon
        await daemon.run()
        
    except KeyboardInterrupt:
        print("Daemon interrupted by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())