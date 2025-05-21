import json
from typing import List, Dict, Tuple, Optional

from .client import APIClient
from .models import User, UserUpdate, ErrorLog, EmailStr

MISSING_EMAILS_FILE = "missing_emails.json"
EMAIL_UPDATE_ERRORS_FILE = "email_update_errors.json"

async def get_users_missing_email(client: APIClient) -> List[User]:
    """Task 1: Get users with missing emails and store them in a JSON file."""
    users = await client.get_users()
    users_missing_email = [user for user in users if not user.email]

    with open(MISSING_EMAILS_FILE, 'w') as f:
        json.dump([user.model_dump() for user in users_missing_email], f, indent=4)
    
    return users_missing_email

def _calculate_email(user: User) -> str:
    """Calculates email based on user type."""
    firstname = user.firstname.lower().replace(" ", "")
    lastname = user.lastname.lower().replace(" ", "")
    if not user.is_external:
        return f"{firstname}.{lastname}@wps-allianz.de"
    else:
        return f"external_{lastname}.{firstname}@wps-allianz.de"

async def update_missing_emails_and_log_errors(client: APIClient) -> Tuple[List[User], List[ErrorLog]]:
    """Task 2 & 3: Update missing emails, ensure uniqueness, and log errors."""
    all_users = await client.get_users()
    users_dict: Dict[int, User] = {user.id: user for user in all_users}
    existing_emails: Dict[EmailStr, int] = {user.email: user.id for user in all_users if user.email}
    
    updated_users: List[User] = []
    error_logs: List[ErrorLog] = []

    users_to_process = [user for user in all_users if not user.email]

    for user_to_update in users_to_process:
        try:
            calculated_email = _calculate_email(user_to_update)

            # Task 3: Check for uniqueness
            if calculated_email in existing_emails and existing_emails[calculated_email] != user_to_update.id:
                error_log = ErrorLog(
                    userId=user_to_update.id,
                    attemptedEmail=calculated_email,
                    error=f"Email already exists for user ID {existing_emails[calculated_email]}"
                )
                error_logs.append(error_log)
                continue # Skip update

            # Update user if email is unique or doesn't exist yet
            user_update_payload = UserUpdate(email=calculated_email)
            # The API docs state that no changes are stored persistently.
            # So, the client.update_user call will return the updated user data as if it were changed.
            updated_user = await client.update_user(user_to_update.id, user_update_payload)
            
            # Simulate the update in our local lists for subsequent checks within this run
            existing_emails[calculated_email] = updated_user.id
            users_dict[updated_user.id].email = calculated_email 
            updated_users.append(users_dict[updated_user.id]) # Append the locally updated user object

        except ValueError as ve:
            error_log = ErrorLog(
                userId=user_to_update.id, 
                attemptedEmail=None,
                error=str(ve)
            )
            error_logs.append(error_log)
        except Exception as e:
            # Catch other potential errors during API call or processing
            calculated_email_str: Optional[str] = None
            if 'calculated_email' in locals() and isinstance(locals()['calculated_email'], str):
                calculated_email_str = locals()['calculated_email']
            
            error_log = ErrorLog(
                userId=user_to_update.id,
                attemptedEmail=calculated_email_str,
                error=f"An unexpected error occurred: {str(e)}"
            )
            error_logs.append(error_log)

    if error_logs:
        with open(EMAIL_UPDATE_ERRORS_FILE, 'w') as f:
            json.dump([log.model_dump() for log in error_logs], f, indent=4)
            
    return updated_users, error_logs 