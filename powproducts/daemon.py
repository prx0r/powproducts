"""Daemon — scheduled collection for PowProducts.

Runs collectors on configured schedules.
Safe to restart — resumes from last cursor.
"""

import json
import time
import signal
import sys
from datetime import datetime, timezone

# Collector schedule
SCHEDULE = {
    'powproducts.collectors.robotshop': {'interval_hours': 6},
}

running = True


def signal_handler(signum, frame):
    global running
    print(f'\nReceived signal {signum}, shutting down gracefully...')
    running = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def run_collector(module_path: str):
    """Import and run a collector."""
    try:
        parts = module_path.rsplit('.', 1)
        module = __import__(parts[0], fromlist=[parts[1]])
        collector_class = getattr(module, parts[1])
        collector = collector_class()
        result = collector.run()
        return {
            'source_id': collector.SOURCE_ID,
            'status': 'ok' if not result.errors else 'error',
            'records_new': result.records_new,
            'records_changed': result.records_changed,
            'records_unchanged': result.records_unchanged,
            'errors': result.errors,
        }
    except Exception as e:
        return {
            'source_id': module_path,
            'status': 'error',
            'error': str(e),
        }


def daemon_loop(interval_seconds: int = 3600):
    """Main daemon loop."""
    print(f'PowProducts daemon starting — interval {interval_seconds}s')
    print('=' * 50)

    last_run = {}

    while running:
        now = datetime.now(timezone.utc)

        for module_path, config in SCHEDULE.items():
            interval_hours = config.get('interval_hours', 24)
            last = last_run.get(module_path)

            if last is None or (now - last).total_seconds() >= interval_hours * 3600:
                print(f'\n[{now.isoformat()}] Running {module_path}...')
                result = run_collector(module_path)
                print(f'  Result: {json.dumps(result, default=str)}')
                last_run[module_path] = now

        # Sleep in small increments to allow signal handling
        for _ in range(min(interval_seconds, 60)):
            if not running:
                break
            time.sleep(1)

    print('Daemon stopped.')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='PowProducts daemon')
    parser.add_argument('--interval', type=int, default=3600, help='Check interval in seconds')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    args = parser.parse_args()

    if args.once:
        for module_path in SCHEDULE:
            result = run_collector(module_path)
            print(json.dumps(result, indent=2, default=str))
    else:
        daemon_loop(args.interval)
