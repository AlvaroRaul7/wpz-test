import httpx
from typing import List, Optional
import os

from .models import User, UserCreate, UserUpdate

# Read BASE_URL from environment variable, with a default
BASE_URL = os.getenv("EXTERNAL_API_BASE_URL", "https://wps-interview.azurewebsites.net")
API_V1_USER_PREFIX = "/api/v1/user"

class APIClient:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(follow_redirects=True)

    async def get_users(self) -> List[User]:
        response = await self.client.get(f"{self.base_url}{API_V1_USER_PREFIX}/")
        response.raise_for_status() # Raise an exception for HTTP errors
        return [User(**user_data) for user_data in response.json()]

    async def get_user(self, user_id: int) -> User:
        response = await self.client.get(f"{self.base_url}{API_V1_USER_PREFIX}/{user_id}/")
        response.raise_for_status()
        return User(**response.json())

    async def create_user(self, user_data: UserCreate) -> User:
        response = await self.client.post(f"{self.base_url}{API_V1_USER_PREFIX}/", json=user_data.model_dump())
        response.raise_for_status()
        # The API returns the created user with an ID, but no actual creation happens.
        # We'll simulate this by adding a dummy ID if not present for consistency with User model
        created_user_data = response.json()
        if "id" not in created_user_data:
            # This is a fallback, ideally the API would return an ID or we'd mock it based on spec
            # For now, let's assume we might need to fetch users again to find it, or assign a temporary one.
            # Given the API spec, it says "the proper response is given back", implying it should include an ID.
            pass # If API behaves as documented, ID should be there.
        return User(**created_user_data)

    async def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        payload = user_data.model_dump(exclude_unset=True) # Only send fields that are set
        if not payload: # If payload is empty, nothing to update
            return await self.get_user(user_id)
            
        response = await self.client.put(f"{self.base_url}{API_V1_USER_PREFIX}/{user_id}/", json=payload)
        response.raise_for_status()
        return User(**response.json())

    async def delete_user(self, user_id: int) -> None:
        response = await self.client.delete(f"{self.base_url}{API_V1_USER_PREFIX}/{user_id}/")
        response.raise_for_status()
        return # No content returned on successful delete

    async def close(self):
        await self.client.aclose()

# Dependency for FastAPI
async def get_api_client():
    client = APIClient()
    try:
        yield client
    finally:
        await client.close() 