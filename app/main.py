from fastapi import FastAPI, Depends, HTTPException
from typing import List, Dict

from . import services
from .client import APIClient, get_api_client
from .models import User, ErrorLog

app = FastAPI(
    title="WPS Interview Challenge API",
    description="API to manage user data and emails.",
    version="1.0.0"
)

@app.get("/users/missing-email", 
         response_model=List[User],
         summary="Task 1: Get Users with Missing Emails",
         description="Retrieves all users, identifies those with missing email addresses, and stores them in missing_emails.json.")
async def get_missing_email_users_route(client: APIClient = Depends(get_api_client)):
    try:
        users = await services.get_users_missing_email(client)
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users/update-emails", 
          response_model=Dict[str, List],
          summary="Task 2 & 3: Update Missing Emails and Handle Duplicates",
          description="Calculates and updates emails for users missing them, ensuring uniqueness and logging errors to email_update_errors.json.")
async def update_emails_route(client: APIClient = Depends(get_api_client)):
    try:
        updated_users, errors = await services.update_missing_emails_and_log_errors(client)
        return {"updated_users": updated_users, "errors": errors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# A simple root endpoint for health check or basic info
@app.get("/", summary="Root Endpoint")
async def read_root():
    return {"message": "Welcome to the WPS Interview Challenge API. See /docs for details."} 