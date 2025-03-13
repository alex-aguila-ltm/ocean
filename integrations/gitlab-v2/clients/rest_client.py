from typing import Any, AsyncIterator, Optional

from loguru import logger

from .base_client import HTTPBaseClient


class RestClient(HTTPBaseClient):
    DEFAULT_PAGE_SIZE = 100
    VALID_GROUP_RESOURCES = ["issues", "merge_requests", "labels"]

    RESOURCE_PARAMS = {
        "labels": {
            "with_counts": True,
            "include_descendant_groups": True,
            "only_group_labels": False,
        }
    }

    def __init__(self, base_url: str, token: str):
        super().__init__(f"{base_url}/api/v4", token)

    async def get_resource(
        self, resource_type: str, params: Optional[dict[str, Any]] = None
    ) -> AsyncIterator[list[dict[str, Any]]]:
        try:
            async for batch in self._make_paginated_request(
                resource_type, params=params
            ):
                yield batch
        except Exception as e:
            logger.error(f"Failed to fetch {resource_type}: {str(e)}")
            raise

    async def get_group_resource(
        self, group_id: str, resource_type: str
    ) -> AsyncIterator[list[dict[str, Any]]]:
        if resource_type not in self.VALID_GROUP_RESOURCES:
            raise ValueError(f"Unsupported resource type: {resource_type}")

        path = f"groups/{group_id}/{resource_type}"
        request_params = self.RESOURCE_PARAMS.get(resource_type, {})

        try:
            async for batch in self._make_paginated_request(
                path,
                params=request_params,
                page_size=self.DEFAULT_PAGE_SIZE,
            ):
                if batch:
                    yield batch
        except Exception as e:
            logger.error(
                f"Failed to fetch {resource_type} for group {group_id}: {str(e)}"
            )
            raise

    async def _make_paginated_request(
        self,
        path: str,
        params: Optional[dict[str, Any]] = None,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        page = 1
        params_dict: dict[str, Any] = params or {}

        while True:
            request_params = {**params_dict, "per_page": page_size, "page": page}
            logger.debug(f"Fetching page {page} from {path}")

            response = await self.send_api_request("GET", path, params=request_params)

            if not response:
                logger.debug(f"No more records to fetch for {path}.")
                break

            yield response

            if len(response) < page_size:
                logger.debug(f"Last page reached for {path}, no more data.")
                break

            page += 1
