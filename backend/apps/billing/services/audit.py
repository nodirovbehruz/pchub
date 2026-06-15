"""Audit log helper — write OperationLog entries from anywhere without boilerplate.

Usage:
    from apps.billing.services.audit import log_action
    log_action(request, LogAction.DB_UPDATE, obj=tariff,
               repr_="Тариф «1 час»", payload={"price": "100"})
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def log_action(request, action, *, obj=None, object_type="", object_id="",
               repr_="", payload=None, club_id=None, shift=None):
    """Create an OperationLog entry. Never raises — best-effort audit.

    - request: DRF request (used for subject + club_id fallback)
    - action: LogAction value
    - obj: optional Django model instance (auto-fills object_type/object_id)
    - repr_: human-readable label
    - payload: dict of extra details
    """
    try:
        from apps.billing.models import OperationLog

        subject = None
        if request is not None:
            user = getattr(request, "user", None)
            if user is not None and getattr(user, "is_authenticated", False):
                subject = user

        if club_id is None and request is not None:
            club_id = getattr(request, "current_club_id", None)
            if not club_id:
                club_id = request.data.get("club") if hasattr(request, "data") else None

        if obj is not None:
            if not object_type:
                object_type = obj.__class__.__name__
            if not object_id:
                object_id = str(getattr(obj, "pk", "") or "")

        OperationLog.objects.create(
            club_id=club_id,
            shift=shift,
            subject=subject,
            object_type=object_type or "",
            object_id=str(object_id or ""),
            object_repr=repr_ or "",
            action=action,
            payload=payload or {},
        )
    except Exception as exc:
        logger.debug("audit log_action failed: %s", exc)
