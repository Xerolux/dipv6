#!/usr/bin/env python3
"""
Health Monitor for DDNS Service
Monitors service health, API connectivity, and system resources
"""

import os
import psutil
import logging
import json
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path("/var/lib/dynipv6")
LOG_DIR = Path("/var/log/dynipv6")


class HealthMonitor:
    """Monitor service health and system resources"""

    def __init__(self):
        """Initialize health monitor"""
        self.start_time = datetime.now()
        self.last_update = None

    def get_service_status(self) -> Dict:
        """Get current service status"""
        uptime = datetime.now() - self.start_time

        return {
            "status": "running",
            "uptime_seconds": uptime.total_seconds(),
            "uptime_human": self._format_uptime(uptime.total_seconds()),
            "timestamp": datetime.now().isoformat()
        }

    def get_system_status(self) -> Dict:
        """Get system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_mb": memory.used // (1024 * 1024),
                "memory_available_mb": memory.available // (1024 * 1024),
                "disk_percent": disk.percent,
                "disk_used_gb": disk.used // (1024 * 1024 * 1024),
                "disk_free_gb": disk.free // (1024 * 1024 * 1024),
                "load_average": os.getloadavg(),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}

    def check_file_permissions(self) -> Dict:
        """Check important file permissions"""
        files_to_check = {
            "config": Path("/etc/dynipv6/config.json"),
            "admin": Path("/etc/dynipv6/admin.json"),
            "encryption_key": Path("/etc/dynipv6/secrets/.key"),
            "data_dir": DATA_DIR,
            "log_dir": LOG_DIR
        }

        results = {}
        for name, path in files_to_check.items():
            if path.exists():
                stat = path.stat()
                results[name] = {
                    "exists": True,
                    "permissions": oct(stat.st_mode)[-3:],
                    "readable": os.access(path, os.R_OK),
                    "writable": os.access(path, os.W_OK),
                    "size_bytes": stat.st_size if path.is_file() else "dir"
                }
            else:
                results[name] = {
                    "exists": False,
                    "permissions": None
                }

        return results

    def get_service_logs(self, lines: int = 20) -> List[str]:
        """Get recent service logs"""
        try:
            log_file = LOG_DIR / "dynipv6.log"
            if log_file.exists():
                with open(log_file, 'r') as f:
                    all_lines = f.readlines()
                    return all_lines[-lines:]
            return []
        except Exception as e:
            logger.error(f"Error reading logs: {e}")
            return []

    def get_dns_records(self) -> Dict:
        """Get current DNS records from local storage"""
        records = {}
        try:
            for file in DATA_DIR.glob("*_*.json"):
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                        domain = data.get('domain', file.stem)
                        records[domain] = {
                            "value": data.get('value'),
                            "type": data.get('type'),
                            "updated": data.get('updated'),
                            "updated_by": data.get('updated_by')
                        }
                except Exception as e:
                    logger.error(f"Error reading {file}: {e}")
            return records
        except Exception as e:
            logger.error(f"Error getting DNS records: {e}")
            return {}

    def get_full_status(self) -> Dict:
        """Get complete system status"""
        return {
            "service": self.get_service_status(),
            "system": self.get_system_status(),
            "files": self.check_file_permissions(),
            "dns_records": self.get_dns_records(),
            "timestamp": datetime.now().isoformat()
        }

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        """Format uptime in human-readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")

        return " ".join(parts)

    def check_alerts(self) -> List[str]:
        """Check for system alerts"""
        alerts = []
        system_status = self.get_system_status()

        if isinstance(system_status, dict):
            if system_status.get('cpu_percent', 0) > 80:
                alerts.append(f"HIGH CPU: {system_status['cpu_percent']}%")

            if system_status.get('memory_percent', 0) > 85:
                alerts.append(f"HIGH MEMORY: {system_status['memory_percent']}%")

            if system_status.get('disk_percent', 0) > 90:
                alerts.append(f"LOW DISK SPACE: {system_status['disk_percent']}% used")

        # Check file permissions
        file_perms = self.check_file_permissions()
        if file_perms.get('config', {}).get('exists'):
            if file_perms['config']['permissions'] != '600':
                alerts.append("Config file permissions not 600!")

        return alerts


def test_health_monitor():
    """Test health monitor"""
    try:
        monitor = HealthMonitor()

        print("=" * 60)
        print("HEALTH MONITOR TEST")
        print("=" * 60)

        # Service status
        print("\n✓ Service Status:")
        service = monitor.get_service_status()
        print(f"  Status: {service['status']}")
        print(f"  Uptime: {service['uptime_human']}")

        # System status
        print("\n✓ System Status:")
        system = monitor.get_system_status()
        if 'error' not in system:
            print(f"  CPU: {system['cpu_percent']}%")
            print(f"  Memory: {system['memory_percent']}% ({system['memory_used_mb']}MB/{system['memory_available_mb']}MB)")
            print(f"  Disk: {system['disk_percent']}% ({system['disk_used_gb']}GB/{system['disk_free_gb']}GB free)")

        # File permissions
        print("\n✓ File Permissions:")
        files = monitor.check_file_permissions()
        for name, info in files.items():
            status = "✓" if info.get('exists') else "✗"
            perms = info.get('permissions', 'N/A')
            print(f"  {status} {name}: {perms}")

        # DNS records
        print("\n✓ DNS Records:")
        records = monitor.get_dns_records()
        if records:
            for domain, data in records.items():
                print(f"  {domain}: {data['value']} (Updated: {data['updated'][:10]})")
        else:
            print("  No records found")

        # Alerts
        print("\n✓ Alerts:")
        alerts = monitor.check_alerts()
        if alerts:
            for alert in alerts:
                print(f"  ⚠ {alert}")
        else:
            print("  No alerts")

        print("\n" + "=" * 60)
        print("Test completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_health_monitor()
