"""Daemon — scheduled collection for PowProducts.

Runs collectors on configured schedules.
Safe to restart — resumes from last cursor.
"""

import importlib
import json
import time
import signal
import sys
from datetime import datetime, timezone

# Collector registry: source_id → {class_path, interval_seconds}
COLLECTORS = {
    "robotshop_uk": {
        "class": "powproducts.collectors.robotshop:RobotShopCollector",
        "interval_seconds": 21600,
    },
    "pci_ids": {
        "class": "powproducts.collectors.pci_ids:PciIdsCollector",
        "interval_seconds": 604800,
    },
    "robot_descriptions": {
        "class": "powproducts.collectors.robot_descriptions:RobotDescriptionsCollector",
        "interval_seconds": 604800,
    },
    "mujoco_menagerie": {
        "class": "powproducts.collectors.mujoco_menagerie:MujocoMenagerieCollector",
        "interval_seconds": 604800,
    },
    "robotis_dynamixel": {
        "class": "powproducts.collectors.robotis:RobotisCollector",
        "interval_seconds": 604800,
    },
}

running = True


def signal_handler(signum, frame):
    global running
    print(f'\nReceived signal {signum}, shutting down gracefully...')
    running = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def load_collector(class_path: str):
    """Load a collector class from 'module:ClassName' string."""
    module_path, class_name = class_path.rsplit(':', 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def run_collector(source_id: str):
    """Import and run a collector by source_id."""
    config = COLLECTORS.get(source_id)
    if not config:
        return {'source_id': source_id, 'status': 'error', 'error': 'not_in_registry'}

    try:
        collector_class = load_collector(config['class'])
        collector = collector_class()
        result = collector.run()
        return {
            'source_id': collector.SOURCE_ID,
            'status': 'ok' if not result.errors else 'error',
            'records_new': result.records_new,
            'records_changed': result.records_changed,
            'records_unchanged': result.records_unchanged,
            'requests_attempted': result.requests_attempted,
            'requests_403': result.requests_403,
            'errors': result.errors,
        }
    except Exception as e:
        return {
            'source_id': source_id,
            'status': 'error',
            'error': str(e),
        }


def daemon_loop(interval_seconds: int = 3600):
    """Main daemon loop."""
    print(f'PowProducts daemon starting — interval {interval_seconds}s')
    print(f'Registered collectors: {list(COLLECTORS.keys())}')
    print('=' * 50)

    last_run = {}

    while running:
        now = datetime.now(timezone.utc)

        for source_id, config in COLLECTORS.items():
            interval = config.get('interval_seconds', 86400)
            last = last_run.get(source_id)

            if last is None or (now - last).total_seconds() >= interval:
                print(f'\n[{now.isoformat()}] Running {source_id}...')
                result = run_collector(source_id)
                print(f'  Result: {json.dumps(result, default=str)}')
                last_run[source_id] = now

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
    parser.add_argument('--source', type=str, help='Run a specific source only')
    args = parser.parse_args()

    if args.once:
        sources = [args.source] if args.source else list(COLLECTORS.keys())
        for source_id in sources:
            result = run_collector(source_id)
            print(json.dumps(result, indent=2, default=str))
    else:
        daemon_loop(args.interval)
