import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Tracks groups locked due to unknown/unapproved persons: {group_jid: unapproved_phone}
_UNAPPROVED_GROUP_LOCKS: Dict[str, str] = {}

def lock_group_due_to_unapproved_person(group_jid: str, unapproved_phone: str) -> None:
    """Locks a group from receiving real-time listings when an unapproved person is present."""
    if group_jid:
        clean_jid = group_jid.strip()
        _UNAPPROVED_GROUP_LOCKS[clean_jid] = unapproved_phone
        logger.warning(f"[GroupSecurity] Locked group {clean_jid} due to unapproved contact: +{unapproved_phone}")

def unlock_group(group_jid: str) -> None:
    """Unlocks a group when the contact is approved or removed."""
    if group_jid:
        clean_jid = group_jid.strip()
        if clean_jid in _UNAPPROVED_GROUP_LOCKS:
            _UNAPPROVED_GROUP_LOCKS.pop(clean_jid, None)
            logger.info(f"[GroupSecurity] Unlocked group {clean_jid}. Real-time listings delivery resumed.")

def is_group_locked(group_jid: str) -> bool:
    """Returns True if the group is currently locked due to an unapproved person."""
    if not group_jid:
        return False
    return group_jid.strip() in _UNAPPROVED_GROUP_LOCKS

def get_group_lock_unapproved_phone(group_jid: str) -> Optional[str]:
    """Returns the unapproved phone number that triggered the lock."""
    if not group_jid:
        return None
    return _UNAPPROVED_GROUP_LOCKS.get(group_jid.strip())
