import json
import pytest
from unittest.mock import patch, AsyncMock
from bitbucket_integration.gitops.file_entity_handler import (
    FileEntityProcessor,
    GitManipulationHandler,
)


def test_file_entity_processor_init():
    """Test initializing FileEntityProcessor."""
    processor = FileEntityProcessor(AsyncMock())
    assert processor.prefix == "file://"


def test_git_manipulation_handler_init():
    """Test initializing GitManipulationHandler."""
    handler = GitManipulationHandler(AsyncMock())
    assert callable(handler._search)


@pytest.mark.asyncio
async def test_file_entity_processor_search_json_success():
    data = {
        "repo": {"name": "test-repo", "mainbranch": {"name": "develop"}},
        "folder": {"path": "src", "commit": {"hash": "commit-hash"}},
    }
    pattern = "file://config.json"
    expected_content = {"key": "value"}
    json_str = json.dumps(expected_content)

    mock_client = AsyncMock()
    mock_client.get_file_content.return_value = json_str

    with patch(
        "bitbucket_integration.gitops.file_entity_handler.BitbucketClient.create_from_ocean_config",
        return_value=mock_client,
    ):
        processor = FileEntityProcessor(
            context=None
        )  # if context isn't used, passing None is fine
        result = await processor._search(data, pattern)
        assert result == expected_content
        mock_client.get_file_content.assert_called_once_with(
            "test-repo", "commit-hash", "src/config.json"
        )


@pytest.mark.asyncio
async def test_file_entity_processor_search_non_json_success():
    data = {
        "repo": {"name": "test-repo", "mainbranch": {"name": "main"}},
        "folder": {"path": "docs", "commit": {"hash": "commit123"}},
    }
    pattern = "file://README.md"
    expected_content = "plain text content"

    mock_client = AsyncMock()
    mock_client.get_file_content.return_value = expected_content

    with patch(
        "bitbucket_integration.gitops.file_entity_handler.BitbucketClient.create_from_ocean_config",
        return_value=mock_client,
    ):
        processor = FileEntityProcessor(context=None)
        result = await processor._search(data, pattern)
        assert result == expected_content
        mock_client.get_file_content.assert_called_once_with(
            "test-repo", "commit123", "docs/README.md"
        )


@pytest.mark.asyncio
async def test_file_entity_processor_search_error_handling():
    data = {
        "repo": {"name": "test-repo", "mainbranch": {"name": "main"}},
        "folder": {"path": "configs", "commit": {"hash": "hash123"}},
    }
    pattern = "file://config.json"

    mock_client = AsyncMock()
    # Simulate an exception when trying to get file content
    mock_client.get_file_content.side_effect = Exception("Test exception")

    with patch(
        "bitbucket_integration.gitops.file_entity_handler.BitbucketClient.create_from_ocean_config",
        return_value=mock_client,
    ):
        processor = FileEntityProcessor(context=None)
        result = await processor._search(data, pattern)
        assert result is None


@pytest.mark.asyncio
async def test_file_entity_processor_search_missing_repo():
    # Data without repo slug
    data = {
        "repo": {},
        "folder": {"path": "src", "commit": {"hash": "hash123"}},
    }
    pattern = "file://config.json"

    processor = FileEntityProcessor(context=None)
    result = await processor._search(data, pattern)
    # Should return None since no repository slug is found
    assert result is None


@pytest.mark.asyncio
async def test_file_entity_processor_search_missing_folder_commit():
    # Data without folder commit info
    data = {
        "repo": {"name": "test-repo", "mainbranch": {"name": "main"}},
        "folder": {"path": "src"},
    }
    pattern = "file://config.json"
    expected_content = '{"key": "value"}'

    mock_client = AsyncMock()
    mock_client.get_file_content.return_value = expected_content

    with patch(
        "bitbucket_integration.gitops.file_entity_handler.BitbucketClient.create_from_ocean_config",
        return_value=mock_client,
    ):
        processor = FileEntityProcessor(context=None)
        result = await processor._search(data, pattern)
        # In this case, since commit hash is missing, it should use the default branch ("main")
        assert result == json.loads(expected_content)
        mock_client.get_file_content.assert_called_once_with(
            "test-repo", "main", "src/config.json"
        )
