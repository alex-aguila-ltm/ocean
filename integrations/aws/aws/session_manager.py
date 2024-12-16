from typing import Any
import typing
import aioboto3
from aws.aws_credentials import AwsCredentials
from loguru import logger
from port_ocean.exceptions.core import OceanAbortException
from auth_provider import CredentialsProvider, OrganizationCredentialsProvider, ApplicationCredentialsProvider

ASSUME_ROLE_DURATION_SECONDS = 3600 

class AccountNotFoundError(OceanAbortException):
    pass


class SessionManager:
    def __init__(self, provider: CredentialsProvider) -> None:
        self._provider = provider
        self._aws_accessible_accounts: list[dict[str, Any]] = []
        self._aws_credentials: list[AwsCredentials] = []
        self._application_account_id: str = ""
        self._application_session: aioboto3.Session | None = None

    async def reset(self) -> None:
        """
        Resets and refreshes all credentials and sessions.
        """
        self._aws_accessible_accounts = []
        self._aws_credentials = []

        application_credentials = await self._provider.get_application_credentials()
        await application_credentials.update_enabled_regions()
        self._application_account_id = application_credentials.account_id
        self._application_session = await application_credentials.create_session()

        self._aws_credentials.append(application_credentials)
        self._aws_accessible_accounts.append({"Id": self._application_account_id, "Name": "No name found"})

        await self._update_available_access_credentials()

    async def _update_available_access_credentials(self) -> None:
        logger.info("Updating AWS credentials")
        accounts = await self._provider.get_all_accessible_accounts(
            typing.cast(aioboto3.Session, self._application_session)
        )

        # Replace the default account placeholder with the real one if found
        for idx, acct in enumerate(accounts):
            if acct["Id"] == self._application_account_id:
                self._aws_accessible_accounts[0] = acct
                break

        async with typing.cast(aioboto3.Session, self._application_session).client("sts") as sts_client:
            for account in accounts:
                if account["Id"] == self._application_account_id:
                    continue
                try:
                    credentials = await self._provider.get_account_credentials(sts_client, account)
                    await credentials.update_enabled_regions()
                    self._aws_credentials.append(credentials)
                    self._aws_accessible_accounts.append(account)
                except Exception:
                    # Skip accounts we cannot assume into
                    pass

        logger.info(f"Found {len(self._aws_credentials)} AWS accounts")

    async def find_account_id_by_session(self, session: aioboto3.Session) -> str:
        session_credentials = await session.get_credentials()  # type: ignore
        frozen_credentials = await session_credentials.get_frozen_credentials()
        for cred in self._aws_credentials:
            if cred.access_key_id == frozen_credentials.access_key:
                return cred.account_id

        raise AccountNotFoundError(
            f"Cannot find credentials linked with this session {session}"
        )

    def find_credentials_by_account_id(self, account_id: str) -> AwsCredentials:
        for cred in self._aws_credentials:
            if cred.account_id == account_id:
                return cred

        if len(self._aws_credentials) == 1:
            return self._aws_credentials[0]

        raise AccountNotFoundError(
            f"Cannot find credentials linked with this account id {account_id}"
        )
