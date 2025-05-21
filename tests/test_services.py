import pytest
import pytest_asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from typing import List, Dict

from app.services import (
    get_users_missing_email,
    update_missing_emails_and_log_errors,
    _calculate_email,
    MISSING_EMAILS_FILE,
    EMAIL_UPDATE_ERRORS_FILE
)
from app.models import User, ErrorLog, EmailStr, UserUpdate
from app.client import APIClient

# Sample user data based on API description
USER_1_INTERNAL_NO_EMAIL = User(id=1, firstname="John", lastname="Doe", email=None, is_external=False)
USER_2_EXTERNAL_NO_EMAIL = User(id=2, firstname="Jane", lastname="Smith", email=None, is_external=True)
USER_3_INTERNAL_WITH_EMAIL = User(id=3, firstname="Peter", lastname="Jones", email="peter.jones@wps-allianz.de", is_external=False)
USER_4_EXTERNAL_WITH_EMAIL = User(id=4, firstname="Alice", lastname="Wonder", email="external_wonder.alice@wps-allianz.de", is_external=True)
USER_5_INTERNAL_NO_EMAIL_DUPLICATE_TARGET = User(id=5, firstname="Peter", lastname="Jones", email=None, is_external=False)
USER_6_INTERNAL_NO_EMAIL_SIMPLE = User(id=6, firstname="Simple", lastname="User", email=None, is_external=False)
USER_7_EXTERNAL_NO_EMAIL_SIMPLE = User(id=7, firstname="Another", lastname="Person", email=None, is_external=True)

ALL_USERS_SAMPLE: List[User] = [
    USER_1_INTERNAL_NO_EMAIL,
    USER_2_EXTERNAL_NO_EMAIL,
    USER_3_INTERNAL_WITH_EMAIL,
    USER_4_EXTERNAL_WITH_EMAIL,
    USER_5_INTERNAL_NO_EMAIL_DUPLICATE_TARGET,
    USER_6_INTERNAL_NO_EMAIL_SIMPLE,
    USER_7_EXTERNAL_NO_EMAIL_SIMPLE
]

@pytest_asyncio.fixture
async def mock_api_client() -> APIClient:
    client = AsyncMock(spec=APIClient)
    
    # Default get_users behavior
    client.get_users.return_value = [u.model_copy(deep=True) for u in ALL_USERS_SAMPLE]

    # Default update_user behavior (can be overridden in tests)
    async def default_mock_update_user(user_id: int, user_data: UserUpdate) -> User:
        # This default implementation should work with the list provided by get_users
        # It simulates finding a user from the *current* list given by get_users and updating it.
        # Tests that modify get_users.return_value should also adjust this or provide their own side_effect.
        users_list = client.get_users.return_value # Use the currently set list
        original_user = next((u for u in users_list if u.id == user_id), None)

        if not original_user:
            # Try falling back to ALL_USERS_SAMPLE if not found in a potentially modified list,
            # but this indicates a potential mismatch in test setup.
            original_user_from_global = next((u for u in ALL_USERS_SAMPLE if u.id == user_id), None)
            if not original_user_from_global:
                 raise Exception(f"User with id {user_id} not found for mock update in default_mock_update_user")
            original_user = original_user_from_global.model_copy(deep=True)


        temp_user_for_update = original_user.model_copy(deep=True)
        updated_fields = user_data.model_dump(exclude_unset=True)
        for key, value in updated_fields.items():
            setattr(temp_user_for_update, key, value)
        
        # Also update in the list that get_users returns for this mock client instance
        for i, u_in_list in enumerate(users_list):
            if u_in_list.id == user_id:
                users_list[i] = temp_user_for_update # Replace in the list
                break
        return temp_user_for_update

    client.update_user = AsyncMock(side_effect=default_mock_update_user)
    return client

@pytest.mark.asyncio
async def test_get_users_missing_email(mock_api_client: APIClient):
    # Ensure get_users returns a fresh copy for this test
    mock_api_client.get_users.return_value = [u.model_copy(deep=True) for u in ALL_USERS_SAMPLE]
    
    with patch('builtins.open', new_callable=MagicMock()) as mock_open:
        with patch('json.dump') as mock_json_dump:
            result = await get_users_missing_email(mock_api_client)

            mock_api_client.get_users.assert_called_once()
            
            expected_missing_ids = {
                USER_1_INTERNAL_NO_EMAIL.id,
                USER_2_EXTERNAL_NO_EMAIL.id,
                USER_5_INTERNAL_NO_EMAIL_DUPLICATE_TARGET.id,
                USER_6_INTERNAL_NO_EMAIL_SIMPLE.id,
                USER_7_EXTERNAL_NO_EMAIL_SIMPLE.id
            }
            assert len(result) == len(expected_missing_ids)
            assert all(isinstance(u, User) for u in result)
            assert {u.id for u in result} == expected_missing_ids

            mock_open.assert_called_once_with(MISSING_EMAILS_FILE, 'w')
            mock_json_dump.assert_called_once()
            dumped_data = mock_json_dump.call_args[0][0]
            assert {d['id'] for d in dumped_data} == expected_missing_ids

def test_calculate_email():
    assert _calculate_email(USER_1_INTERNAL_NO_EMAIL) == "john.doe@wps-allianz.de"
    assert _calculate_email(USER_2_EXTERNAL_NO_EMAIL) == "external_smith.jane@wps-allianz.de"
    user_internal_space = User(id=10, firstname="First Name", lastname="Last Name", email=None, is_external=False)
    user_external_space = User(id=11, firstname="Another Name", lastname="Family Name", email=None, is_external=True)
    assert _calculate_email(user_internal_space) == "firstname.lastname@wps-allianz.de"
    assert _calculate_email(user_external_space) == "external_familyname.anothername@wps-allianz.de"

@pytest.mark.asyncio
async def test_update_missing_emails_and_log_errors_no_duplicates(mock_api_client: APIClient):
    simplified_users_list = [
        USER_1_INTERNAL_NO_EMAIL.model_copy(deep=True), 
        USER_2_EXTERNAL_NO_EMAIL.model_copy(deep=True),
        USER_3_INTERNAL_WITH_EMAIL.model_copy(deep=True),
    ]
    mock_api_client.get_users.return_value = simplified_users_list
    
    with patch('builtins.open', new_callable=MagicMock()) as mock_open:
        with patch('json.dump') as mock_json_dump:
            updated_users, errors = await update_missing_emails_and_log_errors(mock_api_client)

            assert len(errors) == 0
            assert len(updated_users) == 2

            user1_updated = next(u for u in updated_users if u.id == USER_1_INTERNAL_NO_EMAIL.id)
            user2_updated = next(u for u in updated_users if u.id == USER_2_EXTERNAL_NO_EMAIL.id)
            
            assert user1_updated.email == "john.doe@wps-allianz.de"
            assert user2_updated.email == "external_smith.jane@wps-allianz.de"

            assert mock_api_client.update_user.call_count == 2
            mock_api_client.update_user.assert_any_call(USER_1_INTERNAL_NO_EMAIL.id, UserUpdate(email="john.doe@wps-allianz.de"))
            mock_api_client.update_user.assert_any_call(USER_2_EXTERNAL_NO_EMAIL.id, UserUpdate(email="external_smith.jane@wps-allianz.de"))
            
            mock_open.assert_not_called()
            mock_json_dump.assert_not_called()

@pytest.mark.asyncio
async def test_update_missing_emails_with_duplicates_and_errors(mock_api_client: APIClient):
    current_test_users = [u.model_copy(deep=True) for u in ALL_USERS_SAMPLE]
    mock_api_client.get_users.return_value = current_test_users

    with patch('builtins.open', new_callable=MagicMock()) as mock_open:
        with patch('json.dump') as mock_json_dump:
            updated_users, errors = await update_missing_emails_and_log_errors(mock_api_client)

            assert len(errors) == 1
            error_log = errors[0]
            assert isinstance(error_log, ErrorLog)
            assert error_log.userId == USER_5_INTERNAL_NO_EMAIL_DUPLICATE_TARGET.id
            assert error_log.attemptedEmail == "peter.jones@wps-allianz.de"
            assert "Email already exists for user ID 3" in error_log.error

            assert len(updated_users) == 4
            updated_ids = {u.id for u in updated_users}
            assert USER_1_INTERNAL_NO_EMAIL.id in updated_ids
            assert USER_2_EXTERNAL_NO_EMAIL.id in updated_ids
            assert USER_6_INTERNAL_NO_EMAIL_SIMPLE.id in updated_ids
            assert USER_7_EXTERNAL_NO_EMAIL_SIMPLE.id in updated_ids
            assert USER_5_INTERNAL_NO_EMAIL_DUPLICATE_TARGET.id not in updated_ids

            user1_updated = next(u for u in updated_users if u.id == USER_1_INTERNAL_NO_EMAIL.id)
            assert user1_updated.email == "john.doe@wps-allianz.de"

            user6_updated = next(u for u in updated_users if u.id == USER_6_INTERNAL_NO_EMAIL_SIMPLE.id)
            assert user6_updated.email == "simple.user@wps-allianz.de"
            
            user7_updated = next(u for u in updated_users if u.id == USER_7_EXTERNAL_NO_EMAIL_SIMPLE.id)
            assert user7_updated.email == "external_person.another@wps-allianz.de"

            assert mock_api_client.update_user.call_count == 4
            mock_api_client.update_user.assert_any_call(USER_1_INTERNAL_NO_EMAIL.id, UserUpdate(email="john.doe@wps-allianz.de"))
            mock_api_client.update_user.assert_any_call(USER_2_EXTERNAL_NO_EMAIL.id, UserUpdate(email="external_smith.jane@wps-allianz.de"))
            mock_api_client.update_user.assert_any_call(USER_6_INTERNAL_NO_EMAIL_SIMPLE.id, UserUpdate(email="simple.user@wps-allianz.de"))
            mock_api_client.update_user.assert_any_call(USER_7_EXTERNAL_NO_EMAIL_SIMPLE.id, UserUpdate(email="external_person.another@wps-allianz.de"))
            
            called_update_ids = {call.args[0] for call in mock_api_client.update_user.call_args_list}
            assert USER_5_INTERNAL_NO_EMAIL_DUPLICATE_TARGET.id not in called_update_ids

            mock_open.assert_called_once_with(EMAIL_UPDATE_ERRORS_FILE, 'w')
            mock_json_dump.assert_called_once()
            dumped_error_data = mock_json_dump.call_args[0][0]
            assert len(dumped_error_data) == 1
            assert dumped_error_data[0]['userId'] == USER_5_INTERNAL_NO_EMAIL_DUPLICATE_TARGET.id

@pytest.mark.asyncio
async def test_update_missing_emails_api_error_on_update(mock_api_client: APIClient):
    failing_user_id = USER_1_INTERNAL_NO_EMAIL.id
    
    # Keep a reference to the original side_effect if needed, or define a new one cleanly
    original_side_effect = mock_api_client.update_user.side_effect

    async def new_side_effect_update_user(user_id: int, user_data: UserUpdate) -> User:
        if user_id == failing_user_id:
            raise Exception("Simulated API Update Error")
        if original_side_effect: # Check if it was set and callable
            # If original_side_effect is an AsyncMock or coroutine function
            return await original_side_effect(user_id, user_data)
        # Fallback or raise error if original_side_effect is not what's expected
        raise TypeError("Original side_effect not callable as expected")

    mock_api_client.update_user.side_effect = new_side_effect_update_user
    mock_api_client.get_users.return_value = [USER_1_INTERNAL_NO_EMAIL, USER_3_INTERNAL_WITH_EMAIL]

    with patch('builtins.open', new_callable=MagicMock()) as mock_open:
        with patch('json.dump') as mock_json_dump:
            updated_users, errors = await update_missing_emails_and_log_errors(mock_api_client)

            assert len(updated_users) == 0
            assert len(errors) == 1
            error_log = errors[0]
            assert error_log.userId == failing_user_id
            assert error_log.attemptedEmail == "john.doe@wps-allianz.de"
            assert "Simulated API Update Error" in error_log.error

            mock_open.assert_called_once_with(EMAIL_UPDATE_ERRORS_FILE, 'w')
            mock_json_dump.assert_called_once() 