import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PermissionChecker, get_current_user
from app.core.database import get_db_session
from app.core.permissions import (
    REMINDERS_CREATE,
    REMINDERS_DELETE,
    REMINDERS_UPDATE,
    REMINDERS_VIEW,
)
from app.schemas.atm004 import ReminderAckBody, ReminderCreateBody
from app.schemas.reminder import (
    ReminderConfigCreateBody,
    ReminderConfigCreateResponse,
    ReminderConfigGroupListResponse,
    ReminderConfigGroupResponse,
    ReminderConfigResponse,
    ReminderConfigUpdateBody,
    ReminderEntityTypesResponse,
    ReminderModuleSchemaResponse,
    ReminderModuleSummaryResponse,
    ReminderRecipientTypeResponse,
    ReminderSettingsSaveBody,
    ReminderTemplateCatalogResponse,
    ReminderTriggerFieldResponse,
    ReminderWorkflowEventResponse,
)
from app.services.channel_service import ChannelService
from app.services.reminder_config_service import (
    ReminderConfigService,
    ReminderDefinitionSetting,
    ReminderOffsetSetting,
)
from app.services.reminder_resolvers import ReminderResolverFactory
from app.services.reminder_resolvers.base import UnsupportedReminderEntityTypeError
from app.services.reminder_service import ReminderService
from app.services.reminder_template_catalog import ReminderTemplateCatalogService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/reminders",
    tags=["reminders"],
    dependencies=[Depends(get_current_user)],
)


def _serialize(item):
    data = {}
    for key, value in item.__dict__.items():
        if key.startswith("_"):
            continue
        if hasattr(value, "isoformat"):
            data[key] = value.isoformat()
        else:
            data[key] = value
    return data


@router.post("", dependencies=[Depends(PermissionChecker(REMINDERS_CREATE))])
async def create_reminder(body: ReminderCreateBody, session: AsyncSession = Depends(get_db_session)):
    service = ReminderService(session)
    item = await service.create_reminder(**body.model_dump())
    return _serialize(item)


def _serialize_reminder_configs(rows) -> ReminderConfigCreateResponse:
    return ReminderConfigCreateResponse(
        configs=[ReminderConfigResponse.model_validate(row, from_attributes=True) for row in rows],
    )


def _serialize_config_groups(rows: list[dict[str, object]]) -> ReminderConfigGroupListResponse:
    return ReminderConfigGroupListResponse(
        configs=[ReminderConfigGroupResponse.model_validate(row) for row in rows],
    )


def _serialize_module_schema(module_id: str) -> ReminderModuleSchemaResponse:
    try:
        meta = ReminderResolverFactory.get_module_metadata(module_id)
    except UnsupportedReminderEntityTypeError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown reminder module: {module_id}") from exc
    return ReminderModuleSchemaResponse(
        trigger_types=[
            ReminderTriggerFieldResponse(key=item.key, label=item.label, type=item.type)
            for item in meta.trigger_types
        ],
        workflow_events=[
            ReminderWorkflowEventResponse(key=item.key, label=item.label)
            for item in meta.workflow_events
        ],
        recipient_types=[
            ReminderRecipientTypeResponse(id=item.id, label=item.label)
            for item in meta.recipient_types
        ],
        supported_channels=list(meta.supported_channels),
        default_template=meta.default_template,
    )


@router.get(
    "/modules",
    response_model=list[ReminderModuleSummaryResponse],
    dependencies=[Depends(PermissionChecker(REMINDERS_VIEW))],
)
async def list_reminder_modules() -> list[ReminderModuleSummaryResponse]:
    """List modules that registered a ReminderEntityResolver (metadata-driven)."""
    return [
        ReminderModuleSummaryResponse(
            id=item.id,
            name=item.name,
            supports_date=item.supports_date,
            supports_workflow=item.supports_workflow,
        )
        for item in ReminderResolverFactory.list_module_summaries()
    ]


@router.get(
    "/modules/{module}/schema",
    response_model=ReminderModuleSchemaResponse,
    dependencies=[Depends(PermissionChecker(REMINDERS_VIEW))],
)
async def get_reminder_module_schema(module: str) -> ReminderModuleSchemaResponse:
    """Return trigger/recipient/channel schema for one registered module."""
    return _serialize_module_schema(module)


@router.get(
    "/channels",
    response_model=list[str],
    dependencies=[Depends(PermissionChecker(REMINDERS_VIEW))],
)
async def list_reminder_channels() -> list[str]:
    """Platform reminder channels from ChannelService (single source of truth)."""
    return ChannelService.supported_channels()


@router.get(
    "/templates",
    response_model=list[ReminderTemplateCatalogResponse],
    dependencies=[Depends(PermissionChecker(REMINDERS_VIEW))],
)
async def list_reminder_templates() -> list[ReminderTemplateCatalogResponse]:
    """Catalog of known reminder templates (placeholder service until template store exists)."""
    catalog = ReminderTemplateCatalogService()
    return [
        ReminderTemplateCatalogResponse(
            id=item.id,
            name=item.name,
            channel=item.channel,
            subject=item.subject,
            body=item.body,
            module=item.module,
        )
        for item in catalog.list_templates()
    ]


@router.get("/entity-types", response_model=ReminderEntityTypesResponse, dependencies=[Depends(PermissionChecker(REMINDERS_VIEW))])
async def list_reminder_entity_types() -> ReminderEntityTypesResponse:
    return ReminderEntityTypesResponse(
        entity_types=list(ReminderResolverFactory.supported_entity_types()),
    )


@router.put("/config/settings", response_model=ReminderConfigCreateResponse, dependencies=[Depends(PermissionChecker(REMINDERS_UPDATE))])
async def save_reminder_settings(
    body: ReminderSettingsSaveBody,
    session: AsyncSession = Depends(get_db_session),
):
    """Save reminder_configs for an entity from the Reminder Settings UI."""
    service = ReminderConfigService(session)
    try:
        if body.reminders is not None:
            configs = await service.save_entity_definitions(
                organization_id=body.organization_id,
                entity_type=body.entity_type,
                entity_id=body.entity_id,
                definitions=[
                    ReminderDefinitionSetting(
                        channels=reminder.channels,
                        offset_value=reminder.offset_value,
                        offset_unit=reminder.offset_unit,
                        time_of_day=reminder.time_of_day,
                        scheduled_at=reminder.scheduled_at,
                        anchor_type=reminder.anchor_type,
                        anchor_key=reminder.anchor_key,
                        offset_direction=reminder.offset_direction,
                    )
                    for reminder in body.reminders
                ],
                template_key=body.template_key,
                entity_label=body.entity_label,
                sender_name=body.sender_name,
                dnd_start=body.dnd_start,
                dnd_end=body.dnd_end,
            )
        else:
            configs = await service.save_entity_settings(
                organization_id=body.organization_id,
                entity_type=body.entity_type,
                entity_id=body.entity_id,
                channels=body.channels,
                offsets=[
                    ReminderOffsetSetting(
                        offset_value=offset.offset_value,
                        offset_unit=offset.offset_unit,
                        time_of_day=offset.time_of_day,
                        anchor_type=offset.anchor_type,
                        anchor_key=offset.anchor_key,
                        offset_direction=offset.offset_direction,
                    )
                    for offset in body.offsets
                ],
                template_key=body.template_key,
                entity_label=body.entity_label,
                sender_name=body.sender_name,
                dnd_start=body.dnd_start,
                dnd_end=body.dnd_end,
                anchor_type=body.anchor_type,
                anchor_key=body.anchor_key,
                offset_direction=body.offset_direction,
            )
        return _serialize_reminder_configs(configs)
    except Exception as exc:
        logger.exception("REMINDER SETTINGS SAVE ERROR: %s", exc)
        raise


@router.post("/config", response_model=ReminderConfigGroupListResponse, dependencies=[Depends(PermissionChecker(REMINDERS_CREATE))])
async def create_reminder_configs(
    body: ReminderConfigCreateBody,
    session: AsyncSession = Depends(get_db_session),
):
    service = ReminderConfigService(session)
    try:
        if body.reminders is not None:
            await service.save_entity_definitions(
                organization_id=body.organization_id,
                entity_type=body.entity_type,
                entity_id=body.entity_id,
                definitions=[
                    ReminderDefinitionSetting(
                        channels=reminder.channels,
                        offset_value=reminder.offset_value,
                        offset_unit=reminder.offset_unit,
                        time_of_day=reminder.time_of_day,
                        scheduled_at=reminder.scheduled_at,
                        anchor_type=reminder.anchor_type,
                        anchor_key=reminder.anchor_key,
                        offset_direction=reminder.offset_direction,
                    )
                    for reminder in body.reminders
                ],
                dnd_start=body.dnd_start,
                dnd_end=body.dnd_end,
            )
        else:
            await service.create_configs(
                organization_id=body.organization_id,
                entity_type=body.entity_type,
                entity_id=body.entity_id,
                channel=body.channel or "",
                offsets=body.offsets or [],
                offset_unit=body.offset_unit,
                dnd_start=body.dnd_start,
                dnd_end=body.dnd_end,
                anchor_type=body.anchor_type,
                anchor_key=body.anchor_key,
                offset_direction=body.offset_direction,
            )
        groups = await service.list_active_config_groups(
            organization_id=body.organization_id,
            entity_type=body.entity_type,
            entity_id=body.entity_id,
        )
        return _serialize_config_groups(groups)
    except Exception as exc:
        logger.exception("REMINDER CONFIG ERROR: %s", exc)
        print("REMINDER CONFIG ERROR:", str(exc))
        raise


@router.get("/config/{entity_type}/{entity_id}", response_model=ReminderConfigGroupListResponse, dependencies=[Depends(PermissionChecker(REMINDERS_VIEW))])
async def list_reminder_configs(
    entity_type: str,
    entity_id: int,
    organization_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    service = ReminderConfigService(session)
    groups = await service.list_active_config_groups(
        organization_id=organization_id,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    return _serialize_config_groups(groups)


@router.patch("/config/{config_id}", response_model=ReminderConfigGroupResponse, dependencies=[Depends(PermissionChecker(REMINDERS_UPDATE))])
async def update_reminder_config(
    config_id: int,
    body: ReminderConfigUpdateBody,
    session: AsyncSession = Depends(get_db_session),
):
    service = ReminderConfigService(session)
    try:
        payload = body.model_dump(exclude_unset=True)
        channels = payload.pop("channels", None)
        updated = await service.update_config_with_channels(
            config_id,
            updates=payload,
            channels=channels,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    groups = await service.list_active_config_groups(
        organization_id=updated.organization_id,
        entity_type=updated.entity_type,
        entity_id=updated.entity_id,
    )
    for group in groups:
        if int(group["config_id"]) == int(updated.id):
            return ReminderConfigGroupResponse.model_validate(group)
        if updated.channel in set(group.get("channels", [])):
            if (
                int(group["offset_value"]) == int(updated.offset_value)
                and str(group["offset_unit"]) == str(updated.offset_unit)
                and group.get("time_of_day") == updated.time_of_day
                and str(group.get("anchor_type")) == str(updated.anchor_type)
                and str(group.get("anchor_key")) == str(updated.anchor_key)
                and str(group.get("offset_direction")) == str(updated.offset_direction)
            ):
                return ReminderConfigGroupResponse.model_validate(group)
    return ReminderConfigGroupResponse.model_validate(
        {
            "config_id": updated.id,
            "organization_id": updated.organization_id,
            "entity_type": updated.entity_type,
            "entity_id": updated.entity_id,
            "anchor_type": updated.anchor_type,
            "anchor_key": updated.anchor_key,
            "offset_direction": updated.offset_direction,
            "offset_value": updated.offset_value,
            "offset_unit": updated.offset_unit,
            "time_of_day": updated.time_of_day,
            "channels": [updated.channel],
            "is_active": updated.is_active,
        }
    )


@router.delete("/config/{config_id}", dependencies=[Depends(PermissionChecker(REMINDERS_DELETE))])
async def deactivate_reminder_config(
    config_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    service = ReminderConfigService(session)
    try:
        await service.deactivate_config(config_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"message": "Reminder config deactivated successfully"}


@router.post("/{reminder_id}/ack", dependencies=[Depends(PermissionChecker(REMINDERS_UPDATE))])
async def acknowledge_reminder(
    reminder_id: int,
    body: ReminderAckBody,
    session: AsyncSession = Depends(get_db_session),
):
    service = ReminderService(session)
    try:
        item = await service.acknowledge_reminder(reminder_id, actor_user_id=body.actor_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize(item)
