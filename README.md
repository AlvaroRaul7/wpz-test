# WPS Interview Challenge

This project implements a FastAPI application to manage user data from an external API, focusing on email address validation and updates.

## Project Structure

```
├── app
│   ├── __init__.py
│   ├── main.py         # FastAPI application
│   ├── services.py     # Business logic for tasks
│   ├── models.py       # Pydantic models
│   └── client.py       # HTTP client for external API
├── tests
│   ├── __init__.py
│   └── test_services.py # Unit tests for services
├── missing_emails.json # Output of Task 1
├── email_update_errors.json # Output of Task 3
├── requirements.txt    # Project dependencies
└── README.md           # This file
```

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd wps-interview-challenge
    ```

2.  **Create a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

The application can be configured using environment variables:

-   `EXTERNAL_API_BASE_URL`: The base URL for the external user API. Defaults to `https://wps-interview.azurewebsites.net`.
-   `PORT`: The port Uvicorn will listen on (primarily for local execution, Dockerfile sets its own). Defaults to `8000` if `uvicorn` command is run without `--port`.

## Running the Application

To start the FastAPI application, run:

```bash
uvicorn app.main:app --reload
```

The API documentation (Swagger UI) will be available at [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs).

## Running Tests

To run the unit tests:

```bash
pytest
```

## Dockerizing the Application

A `Dockerfile` is provided to containerize the application.

1.  **Build the Docker image:**
    Make sure you have Docker installed and running. In the project root directory, run:
    ```bash
    docker build -t wps-user-app .
    ```

2.  **Run the Docker container:**
    ```bash
    docker run -p 8001:8000 wps-user-app
    ```
    This command will start the application inside a Docker container. Port 8000 inside the container (where Uvicorn runs) will be mapped to port 8001 on your host machine. You can then access the API at `http://127.0.0.1:8001` and the API docs at `http://127.0.0.1:8001/docs`.

    You can override the external API URL when running the Docker container by setting the `EXTERNAL_API_BASE_URL` environment variable:
    ```bash
    docker run -e EXTERNAL_API_BASE_URL="your_custom_api_url" -p 8001:8000 wps-user-app
    ```

## Tasks

### Task 1: Get Missing Emails
-   **Endpoint:** `GET /users/missing-email`
-   **Description:** Retrieves all users from the external API, identifies those with missing email addresses, and stores their information in `missing_emails.json`.

### Task 2 & 3: Update Missing Emails & Handle Duplicates
-   **Endpoint:** `POST /users/update-emails`
-   **Description:**
    -   Calculates email addresses for users missing them:
        -   Internal Users: `<firstname>.<lastname>@wps-allianz.de`
        -   External Users: `external_<lastname>.<firstname>@wps-allianz.de`
    -   Updates these users via the external API.
    -   Ensures email uniqueness. If a calculated email already exists for another user, the update for the current user is skipped, and an error is logged in `email_update_errors.json`.

## Testing the API Endpoints

Once the application is running (using `uvicorn app.main:app --reload`), you can test the endpoints using a tool like `curl` or an API client like Postman or Insomnia.

### 1. Get Users with Missing Emails (Task 1)

This endpoint will identify users without an email and save them to `missing_emails.json` in the project root.

```bash
curl -X GET "http://127.0.0.1:8001/users/missing-email" -H "accept: application/json"
```

**Expected Output (example snippet in terminal):**
```json
[
  {
    "id": 1,
    "firstname": "John",
    "lastname": "Doe",
    "email": null,
    "type": "internal"
  },
  // ... other users missing emails
]
```
- Check `missing_emails.json` for the full list.

### 2. Update Missing Emails (Task 2 & 3)

This endpoint will attempt to calculate and set emails for users who are missing them. It handles duplicates and logs errors to `email_update_errors.json`. Since the endpoint doesn't require a request body, the POST request is simple.

```bash
curl -X POST "http://127.0.0.1:8001/users/update-emails" -H "accept: application/json"
```
(Note: For some `curl` versions or configurations, you might need to add `-d ''` for an empty body to ensure it's treated as a POST request, e.g., `curl -X POST "http://127.0.0.1:8001/users/update-emails" -H "accept: application/json" -d ''`)

**Expected Output (example snippet in terminal):**
```json
{
  "updated_users": [
    {
      "id": 1,
      "firstname": "John",
      "lastname": "Doe",
      "email": "john.doe@wps-allianz.de",
      "type": "internal"
    },
    // ... other successfully updated users
  ],
  "errors": [
    {
      "userId": 5,
      "attemptedEmail": "peter.jones@wps-allianz.de",
      "error": "Email already exists for user ID 3"
    }
    // ... other errors encountered
  ]
}
```
- Check `email_update_errors.json` for any logged errors.
- You can call the `GET /users/missing-email` endpoint again to see if the list of users missing emails has changed (it should be empty or smaller, depending on the API's non-persistent nature . )Since the external API doesn't persist changes, re-running this will likely show the original state unless you are inspecting the immediate response or files generated.

### Root Endpoint

To check if the API is running:
```bash
curl -X GET "http://127.0.0.1:8001/" -H "accept: application/json"
```

**Expected Output:**
```