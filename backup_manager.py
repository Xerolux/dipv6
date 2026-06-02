#!/usr/bin/env python3
"""
Backup management for critical configuration files
Automatic versioning and restore capability
"""

import shutil
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Critical files to backup
CRITICAL_FILES = [
    '/etc/dynipv6/config.json',
    '/etc/dynipv6/admin.json',
    '/etc/letsencrypt/live',
]

BACKUP_DIR = Path('/etc/dynipv6/backups')
MAX_BACKUPS_PER_FILE = 10


class BackupManager:
    """Manage backups of critical configuration files"""

    def __init__(self, backup_dir: Path = BACKUP_DIR):
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_file = self.backup_dir / 'manifest.json'
        self.load_manifest()

    def load_manifest(self):
        """Load backup manifest"""
        if self.manifest_file.exists():
            with open(self.manifest_file, 'r') as f:
                self.manifest = json.load(f)
        else:
            self.manifest = {}

    def save_manifest(self):
        """Save backup manifest"""
        with open(self.manifest_file, 'w') as f:
            json.dump(self.manifest, f, indent=2)

    def backup_file(self, file_path: str, description: str = "") -> Optional[Dict]:
        """
        Create backup of a file

        Args:
            file_path: Full path to file to backup
            description: Optional description of the backup

        Returns:
            Backup info dict or None on failure
        """
        try:
            path = Path(file_path)

            if not path.exists():
                logger.warning(f"File to backup not found: {file_path}")
                return None

            # Create backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{path.name}.{timestamp}.backup"
            backup_path = self.backup_dir / backup_name

            # Copy file
            if path.is_file():
                shutil.copy2(path, backup_path)
            else:
                shutil.copytree(path, backup_path, dirs_exist_ok=True)

            # Update manifest
            if file_path not in self.manifest:
                self.manifest[file_path] = []

            backup_info = {
                'timestamp': timestamp,
                'backup_path': str(backup_path),
                'description': description,
                'size': self._get_size(backup_path)
            }

            self.manifest[file_path].append(backup_info)

            # Keep only MAX_BACKUPS_PER_FILE recent backups
            self._cleanup_old_backups(file_path)
            self.save_manifest()

            logger.info(f"Backup created: {backup_path}")
            return backup_info

        except Exception as e:
            logger.error(f"Error backing up {file_path}: {e}")
            return None

    def restore_file(self, file_path: str, backup_index: int = 0) -> bool:
        """
        Restore file from backup

        Args:
            file_path: Full path to file to restore
            backup_index: Index of backup to restore (0 = most recent)

        Returns:
            True if successful, False otherwise
        """
        try:
            if file_path not in self.manifest or not self.manifest[file_path]:
                logger.error(f"No backups found for {file_path}")
                return False

            backups = self.manifest[file_path]
            if backup_index >= len(backups):
                logger.error(f"Backup index out of range")
                return False

            # Get backup (most recent first)
            backup_info = backups[-(backup_index + 1)]
            backup_path = Path(backup_info['backup_path'])

            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False

            # Backup current file first
            self.backup_file(file_path, "Pre-restore backup")

            # Restore
            original_path = Path(file_path)
            if original_path.exists():
                original_path.unlink() if original_path.is_file() else shutil.rmtree(original_path)

            if backup_path.is_file():
                shutil.copy2(backup_path, original_path)
            else:
                shutil.copytree(backup_path, original_path)

            logger.info(f"Restored {file_path} from {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Error restoring {file_path}: {e}")
            return False

    def list_backups(self, file_path: str) -> List[Dict]:
        """Get list of backups for a file"""
        if file_path not in self.manifest:
            return []

        # Return in reverse chronological order (most recent first)
        return list(reversed(self.manifest[file_path]))

    def delete_backup(self, file_path: str, backup_index: int) -> bool:
        """Delete a specific backup"""
        try:
            if file_path not in self.manifest or backup_index >= len(self.manifest[file_path]):
                return False

            backup_info = self.manifest[file_path].pop(backup_index)
            backup_path = Path(backup_info['backup_path'])

            if backup_path.exists():
                if backup_path.is_file():
                    backup_path.unlink()
                else:
                    shutil.rmtree(backup_path)

            self.save_manifest()
            logger.info(f"Deleted backup: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Error deleting backup: {e}")
            return False

    def _cleanup_old_backups(self, file_path: str):
        """Keep only MAX_BACKUPS_PER_FILE recent backups"""
        if file_path in self.manifest:
            backups = self.manifest[file_path]
            if len(backups) > MAX_BACKUPS_PER_FILE:
                # Delete oldest backups
                for old_backup in backups[:-MAX_BACKUPS_PER_FILE]:
                    try:
                        backup_path = Path(old_backup['backup_path'])
                        if backup_path.exists():
                            if backup_path.is_file():
                                backup_path.unlink()
                            else:
                                shutil.rmtree(backup_path)
                    except Exception as e:
                        logger.warning(f"Error deleting old backup: {e}")

                # Update manifest
                self.manifest[file_path] = backups[-MAX_BACKUPS_PER_FILE:]

    def _get_size(self, path: Path) -> str:
        """Get human-readable size of file/directory"""
        try:
            if path.is_file():
                size = path.stat().st_size
            else:
                size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())

            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024

            return f"{size:.1f} TB"
        except:
            return "Unknown"


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: backup_manager.py <backup|restore|list> <file_path> [backup_index]")
        sys.exit(1)

    action = sys.argv[1]
    file_path = sys.argv[2] if len(sys.argv) > 2 else None
    backup_index = int(sys.argv[3]) if len(sys.argv) > 3 else 0

    manager = BackupManager()

    if action == "backup":
        if not file_path:
            print("Error: file_path required")
            sys.exit(1)
        result = manager.backup_file(file_path)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result else 1)

    elif action == "restore":
        if not file_path:
            print("Error: file_path required")
            sys.exit(1)
        success = manager.restore_file(file_path, backup_index)
        sys.exit(0 if success else 1)

    elif action == "list":
        if not file_path:
            print("Error: file_path required")
            sys.exit(1)
        backups = manager.list_backups(file_path)
        print(json.dumps(backups, indent=2))
        sys.exit(0)

    else:
        print(f"Error: Unknown action '{action}'")
        sys.exit(1)
