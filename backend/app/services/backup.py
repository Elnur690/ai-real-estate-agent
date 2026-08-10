import os
import gzip
import shutil
import logging
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)

BACKUP_DIR = Path("/app/backups") if os.path.exists("/app") else Path(__file__).parent.parent.parent / "backups"

class BackupService:
    @staticmethod
    def get_backup_dir() -> Path:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        return BACKUP_DIR

    @staticmethod
    def create_backup() -> Dict[str, Any]:
        """Create a compressed database backup for PostgreSQL or SQLite."""
        backup_dir = BackupService.get_backup_dir()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        db_url = settings.DATABASE_URL.lower()

        if "postgresql" in db_url or "postgres" in db_url:
            filename = f"realestate_pg_{timestamp}.sql.gz"
            filepath = backup_dir / filename
            
            # Extract Postgres credentials from SYNC_DATABASE_URL or DATABASE_URL
            raw_url = settings.SYNC_DATABASE_URL
            cmd = f"pg_dump {raw_url} | gzip > {filepath}"
            try:
                subprocess.run(cmd, shell=True, check=True)
                size_bytes = filepath.stat().st_size
                logger.info(f"[BackupService] PostgreSQL backup created: {filename} ({size_bytes} bytes)")
                BackupService.rotate_backups()
                return {"success": True, "filename": filename, "path": str(filepath), "size_bytes": size_bytes}
            except Exception as e:
                logger.error(f"[BackupService] PostgreSQL backup error: {e}")
                return {"success": False, "error": str(e)}
        else:
            # SQLite Backup
            filename = f"realestate_sqlite_{timestamp}.db.gz"
            filepath = backup_dir / filename
            source_db = Path("./realestate.db")
            
            if not source_db.exists():
                source_db = Path(__file__).parent.parent.parent / "realestate.db"

            try:
                if source_db.exists():
                    with open(source_db, 'rb') as f_in:
                        with gzip.open(filepath, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    size_bytes = filepath.stat().st_size
                    logger.info(f"[BackupService] SQLite backup created: {filename} ({size_bytes} bytes)")
                    BackupService.rotate_backups()
                    return {"success": True, "filename": filename, "path": str(filepath), "size_bytes": size_bytes}
                else:
                    logger.warning("[BackupService] SQLite database file not found for backup.")
                    return {"success": False, "error": "Database file not found"}
            except Exception as e:
                logger.error(f"[BackupService] SQLite backup error: {e}")
                return {"success": False, "error": str(e)}

    @staticmethod
    def rotate_backups(retention_days: int = 30):
        """Clean up backup files older than retention_days."""
        backup_dir = BackupService.get_backup_dir()
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        
        for p in backup_dir.glob("*.gz"):
            try:
                mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
                if mtime < cutoff:
                    p.unlink()
                    logger.info(f"[BackupService] Pruned old backup: {p.name}")
            except Exception as e:
                logger.error(f"[BackupService] Error pruning {p.name}: {e}")

    @staticmethod
    def list_backups() -> List[Dict[str, Any]]:
        """List all available backup snapshots."""
        backup_dir = BackupService.get_backup_dir()
        backups = []
        for p in sorted(backup_dir.glob("*.gz"), reverse=True):
            stat = p.stat()
            backups.append({
                "filename": p.name,
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            })
        return backups
