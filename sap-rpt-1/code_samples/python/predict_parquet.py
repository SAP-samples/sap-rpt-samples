import json
from pathlib import Path

import requests

# API Configuration
# Note: Replace the placeholder "XXXXXXXXXX" values with your actual configuration.
API_URL = "XXXXXXXXXX/predict_parquet"  # can refer to the readme for the exact format
AI_RESOURCE_GROUP = "XXXXXXXXXX"  # e.g., "default"

# OAuth Configuration
# You can get the credentials from your BTP service key.
# Consider using environment variables and ensure handling secrets in a secure way.
OAUTH_CONFIG = {
    "auth_url": "XXXXXXXXXX/oauth/token",
    "client_id": "XXXXXXXXXX",
    "client_secret": "XXXXXXXXXX",
}


def get_access_token():
    """Get OAuth2 access token using client credentials flow."""
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


def predict_parquet_file(access_token, file_path):
    """
    Upload a parquet file and make predictions for multiple columns.

    Args:
        access_token: OAuth2 access token
        file_path: Path to the parquet file

    Returns:
        API response as dictionary
    """
    # Configure predictions for 'stock' columns with PLACEHOLDER
    prediction_config = {
        "target_columns": [
            {"name": "category", "prediction_placeholder": "PLACEHOLDER"}
        ]
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "AI-Resource-Group": AI_RESOURCE_GROUP,
    }

    with open(file_path, "rb") as f:
        files = {"file": (Path(file_path).name, f, "application/octet-stream")}

        data = {
            "prediction_config": json.dumps(prediction_config),
            "parse_data_types": "false",
        }

        response = requests.post(API_URL, headers=headers, files=files, data=data)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Request failed: {response.status_code} - {response.text}")


if __name__ == "__main__":
    HERE = Path(__file__).parent
    parquet_file = HERE.parent / "data" / "product_data.parquet"

    try:
        # Step 1: Get access token
        print("Obtaining access token...")
        access_token = get_access_token()
        print("Access token obtained successfully!")

        # Step 2: Make prediction with parquet file
        print(f"Uploading {parquet_file} and making predictions...")
        result = predict_parquet_file(access_token=access_token, file_path=parquet_file)

        print("Prediction successful!")
        print(json.dumps(result, indent=2))

    except FileNotFoundError:
        print(f"Error: File '{parquet_file}' not found")
    except Exception as e:
        print(f"Error: {e}")
