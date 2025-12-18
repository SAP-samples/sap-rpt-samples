import json

import requests

# API Configuration
# Note: Replace the placeholder "XXXXXXXXXX" values with your actual configuration.
API_URL = "XXXXXXXXXX/predict"  # can refer to the readme for the exact format
AI_RESOURCE_GROUP = "XXXXXXXXXX"  # e.g., "default"

# OAuth Configuration
# You can get the credentials from your BTP service key.
# Consider using environment variables and ensure handling secrets in a secure way.
OAUTH_CONFIG = {
    "auth_url": "XXXXXXXXXX/oauth/token",
    "client_id": "XXXXXXXXXX",
    "client_secret": "XXXXXXXXXX",
}

# Request payload
payload = {
    "index_column": "id",
    "prediction_config": {
        "target_columns": [
            {
                "name": "category",
                "prediction_placeholder": "?",
                "task_type": "classification",
            }
        ]
    },
    "parse_data_types": "true",
    "data_schema": {
        "id": {"dtype": "numeric"},
        "product": {"dtype": "string"},
        "price": {"dtype": "numeric"},
        "category": {"dtype": "string"},
        "stock": {"dtype": "numeric"},
        "production_date": {"dtype": "date"},
    },
    "rows": [
        {
            "id": 1,
            "product": "Laptop",
            "price": 899,
            "category": "Electronics",
            "stock": "150",
            "production_date": "2024-01-15",
        },
        {
            "id": 2,
            "product": "Mouse",
            "price": 25,
            "category": "Accessories",
            "stock": "500",
            "production_date": "2024-02-20",
        },
        {
            "id": 3,
            "product": "Keyboard",
            "price": 75,
            "category": "Accessories",
            "stock": "320",
            "production_date": "2024-03-10",
        },
        {
            "id": 4,
            "product": "Monitor",
            "price": 350,
            "category": "?",
            "stock": "200",
            "production_date": "2024-03-25",
        },
    ],
}


def get_access_token():
    """
    Get OAuth2 access token using client credentials flow.
    """
    token_data = {
        "grant_type": "client_credentials",
        "client_id": OAUTH_CONFIG["client_id"],
        "client_secret": OAUTH_CONFIG["client_secret"],
    }

    response = requests.post(
        OAUTH_CONFIG["auth_url"],
        data=token_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(
            f"Failed to get access token: {response.status_code} - {response.text}"
        )


def make_prediction(access_token, prediction_data):
    """
    Make a prediction request to the SAP Foundation Model API.

    Args:
        access_token: OAuth2 access token
        prediction_data: Dictionary containing prediction configuration and data

    Returns:
        API response as dictionary
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "AI-Resource-Group": AI_RESOURCE_GROUP,
    }

    response = requests.post(API_URL, headers=headers, json=prediction_data)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Prediction failed: {response.status_code} - {response.text}")


if __name__ == "__main__":
    # Step 1: Get access token
    print("Obtaining access token...")
    access_token = get_access_token()
    print("Access token obtained successfully!")

    # Step 2: Make prediction request
    try:
        result = make_prediction(access_token, payload)
        print("Prediction successful!")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")
