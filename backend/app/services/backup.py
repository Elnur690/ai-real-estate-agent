import os
import json
import gzip
import shutil
import logging
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.tenant import Tenant
from app.models.saved_search import SavedSearch
from app.models.match import Match

logger = logging.getLogger(__name__)

BACKUP_DIR = Path("/app/backups") if os.path.exists("/app") else Path(__file__).parent.parent.parent / "backups"

class BackupService:
    @staticmethod
    def get_backup_dir() -> Path:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        return BACKUP_DIR

    @staticmethod
    def create_backup() -> Dict[str, Any]:
        """Create a full database system backup."""
        backup_dir = BackupService.get_backup_dir()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        db_url = settings.DATABASE_URL.lower()

        if "postgresql" in db_url or "postgres" in db_url:
            filename = f"realestate_pg_{timestamp}.sql.gz"
            filepath = backup_dir / filename
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
    async def create_tenant_backup(db: AsyncSession, tenant_id: int) -> Dict[str, Any]:
        """Generate a tenant-specific data backup package (BaaS Plan feature)."""
        stmt_t = select(Tenant).where(Tenant.id == tenant_id)
        res_t = await db.execute(stmt_t)
        tenant = res_t.scalars().first()
        if not tenant:
            return {"success": False, "error": "Tenant not found"}

        # Fetch Saved Searches
        stmt_s = select(SavedSearch).where(SavedSearch.tenant_id == tenant_id)
        res_s = await db.execute(stmt_s)
        searches = res_s.scalars().all()

        # Fetch Matches
        stmt_m = select(Match).where(Match.tenant_id == tenant_id)
        res_m = await db.execute(stmt_m)
        matches = res_m.scalars().all()

        backup_data = {
            "tenant": {
                "id": tenant.id,
                "name": tenant.name,
                "plan": tenant.plan,
                "phone": tenant.phone,
                "preferred_channel": tenant.preferred_channel,
                "digest_mode": tenant.digest_mode,
                "backup_frequency_days": tenant.backup_frequency_days,
                "exported_at": datetime.now(timezone.utc).isoformat()
            },
            "saved_searches": [
                {
                    "id": s.id,
                    "district": s.district,
                    "min_price": s.min_price,
                    "max_price": s.max_price,
                    "min_rooms": s.min_rooms,
                    "max_rooms": s.max_rooms,
                    "seller_type": s.seller_type,
                    "building_type": s.building_type,
                    "is_active": s.is_active
                }
                for s in searches
            ],
            "matches_count": len(matches)
        }

        backup_dir = BackupService.get_backup_dir() / "tenants"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"tenant_{tenant_id}_backup_{timestamp}.json.gz"
        filepath = backup_dir / filename

        json_bytes = json.dumps(backup_data, indent=2, ensure_ascii=False).encode('utf-8')
        with gzip.open(filepath, 'wb') as f_out:
            f_out.write(json_bytes)

        tenant.last_backup_at = datetime.now(timezone.utc)
        await db.commit()

        size_bytes = filepath.stat().st_size
        logger.info(f"[BackupService] Tenant {tenant_id} backup created: {filename} ({size_bytes} bytes)")
        return {"success": True, "tenant_id": tenant_id, "filename": filename, "size_bytes": size_bytes}

    @staticmethod
    async def run_scheduled_tenant_backups(db: AsyncSession) -> int:
        """Automated Celery Beat job to generate tenant backups based on plan frequency."""
        stmt = select(Tenant).where(Tenant.status == "active", Tenant.backup_enabled == True)
        res = await db.execute(stmt)
        tenants = res.scalars().all()

        now = datetime.now(timezone.utc)
        created_count = 0

        for t in tenants:
            freq = t.backup_frequency_days or 7
            due = False
            if not t.last_backup_at:
                due = True
            else:
                last_dt = t.last_backup_at if t.last_backup_at.tzinfo else t.last_backup_at.replace(tzinfo=timezone.utc)
                if last_dt + timedelta(days=freq) <= now:
                    due = True

            if due:
                res_b = await BackupService.create_tenant_backup(db, t.id)
                if res_b.get("success"):
                    created_count += 1

        return created_count

    @staticmethod
    def rotate_backups(retention_days: int = 30):
        backup_dir = BackupService.get_backup_dir()
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        for p in backup_dir.glob("*.gz"):
            try:
                mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
                if mtime < cutoff:
                    p.unlink()
            except Exception as e:
                logger.error(f"[BackupService] Error pruning {p.name}: {e}")

    @staticmethod
    def list_backups() -> List[Dict[str, Any]]:
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
