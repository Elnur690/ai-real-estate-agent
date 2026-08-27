import pytest
from unittest.mock import AsyncMock, MagicMock
from app.models.tenant import Tenant
from app.models.saved_search import SavedSearch
from app.bot.command_handler import BotCommandHandler

@pytest.mark.asyncio
async def test_block_agent_deleting_other_agent_search():
    mock_db = AsyncMock()
    tenant = Tenant(id=1, name="Test Agency", phone="+994501112233", preferred_channel="whatsapp", allowed_group_jids=[])

    # Search #24 belongs to Agent A (994501112233)
    search_24 = SavedSearch(
        id=24,
        tenant_id=1,
        name="Axtarış: Nərimanov",
        raw_criteria_text="Nərimanovda 2 otaq",
        destination_chat_id="994501112233",
        created_by_sender_id="994501112233",
        is_active=True
    )

    mock_res_t = MagicMock()
    mock_res_t.scalars.return_value.first.return_value = tenant
    mock_res_24 = MagicMock()
    mock_res_24.scalars.return_value.first.return_value = search_24
    mock_res_app = MagicMock()
    mock_res_app.scalar_one_or_none.return_value = "RealEstate AI"

    mock_db.execute.side_effect = [mock_res_app, mock_res_t, mock_res_24]

    # Agent B (994559998877) tries to delete Search #24
    response = await BotCommandHandler.handle_incoming_message(
        db=mock_db,
        channel="whatsapp",
        sender_id="994559998877",
        sender_name="Agent B",
        instance_name="tenant_1",
        raw_text="sil 24"
    )

    assert "İcazə verilmədi" in response
    assert "başqa bir agentə aiddir" in response
    assert search_24.is_active is True  # Search #24 is NOT deleted!

@pytest.mark.asyncio
async def test_allow_agent_deleting_own_search():
    mock_db = AsyncMock()
    tenant = Tenant(id=1, name="Test Agency", phone="+994501112233", preferred_channel="whatsapp", allowed_group_jids=[])

    # Search #25 belongs to Agent B (994559998877)
    search_25 = SavedSearch(
        id=25,
        tenant_id=1,
        name="Axtarış: Nərimanov",
        raw_criteria_text="Nərimanovda 2 otaq",
        destination_chat_id="994559998877",
        created_by_sender_id="994559998877",
        is_active=True
    )

    mock_res_t = MagicMock()
    mock_res_t.scalars.return_value.first.return_value = tenant
    mock_res_25 = MagicMock()
    mock_res_25.scalars.return_value.first.return_value = search_25
    mock_res_app = MagicMock()
    mock_res_app.scalar_one_or_none.return_value = "RealEstate AI"

    mock_db.execute.side_effect = [mock_res_app, mock_res_t, mock_res_25]

    # Agent B (994559998877) deletes their own Search #25
    response = await BotCommandHandler.handle_incoming_message(
        db=mock_db,
        channel="whatsapp",
        sender_id="994559998877",
        sender_name="Agent B",
        instance_name="tenant_1",
        raw_text="/sil 25"
    )

    assert "silindi" in response
    assert search_25.is_active is False

@pytest.mark.asyncio
async def test_block_group_cross_deletion():
    mock_db = AsyncMock()
    tenant = Tenant(id=1, name="Test Agency", phone="+994501112233", preferred_channel="whatsapp", allowed_group_jids=["120363011111111111@g.us", "120363022222222222@g.us"])

    # Search #24 belongs to Group 1
    search_24 = SavedSearch(
        id=24,
        tenant_id=1,
        name="Axtarış: Nərimanov",
        raw_criteria_text="Nərimanovda 2 otaq",
        destination_chat_id="120363011111111111@g.us",
        is_active=True
    )

    mock_res_t = MagicMock()
    mock_res_t.scalars.return_value.first.return_value = tenant
    mock_res_24 = MagicMock()
    mock_res_24.scalars.return_value.first.return_value = search_24
    mock_res_app = MagicMock()
    mock_res_app.scalar_one_or_none.return_value = "RealEstate AI"

    mock_db.execute.side_effect = [mock_res_app, mock_res_t, mock_res_24]

    # Command executed in Group 2
    response = await BotCommandHandler.handle_incoming_message(
        db=mock_db,
        channel="whatsapp",
        sender_id="120363022222222222@g.us",
        sender_name="Group 2",
        instance_name="tenant_1",
        raw_text="/sil 24"
    )

    assert "İcazə verilmədi" in response
    assert "başqa bir WhatsApp qrupuna/agentə aiddir" in response
    assert search_24.is_active is True
