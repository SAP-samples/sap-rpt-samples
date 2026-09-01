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


def get_target_column_config(prediction_data: dict) -> dict:
    """
    Return the first target column config from the request.

    This sample predicts one target column. If you predict multiple target columns,
    apply the same idea per target column.
    """
    return prediction_data["prediction_config"]["target_columns"][0]


def find_query_row_positions(prediction_data: dict) -> list[int]:
    """
    Find query rows in the original API input.

    Query rows are rows where the target column contains the configured
    prediction placeholder. The row positions returned here are zero-based
    positions in prediction_data["rows"].
    """
    target_config = get_target_column_config(prediction_data)
    target_name = target_config["name"]
    placeholder = target_config["prediction_placeholder"]

    return [
        row_idx
        for row_idx, row in enumerate(prediction_data["rows"])
        if row.get(target_name) == placeholder
    ]


def print_input_row_index(prediction_data: dict) -> None:
    """
    Print the sequential row index used by top_relevant_context_rows.

    Important: top_relevant_context_rows returns indices into ALL rows sent to
    the API. These are zero-based row positions in payload["rows"], not values
    from the index_column (here: "id") and not positions in a filtered
    context-only table.
    """
    print("\nFirst five input rows (zero-based row index):")
    for row_idx, row in enumerate(prediction_data["rows"][:5]):
        print(f"  API row {row_idx}: {row}")


def print_prediction_summary(result: dict, prediction_data: dict) -> None:
    """
    Print one readable block per query row: the predicted value, its
    confidence, and (when explanations were requested) why the model
    predicted it.

    Predictions and the explanation arrays are all returned in query-row
    order, so we line them up by position. find_query_row_positions maps that
    order back to the original row in payload["rows"] so the output can say
    "query row 0 = API row 3".

    The RPT response contains:
      - predictions: the predicted value(s) and confidence per query row
      - explanations.top_column_scores: most influential feature columns
      - explanations.top_relevant_context_rows: zero-based indices of the most
        relevant context rows into the complete input table (payload["rows"])
    """
    predictions = result.get("predictions")
    if not predictions:
        print("\nNo predictions returned.")
        return

    target_name = get_target_column_config(prediction_data)["name"]
    query_row_positions = find_query_row_positions(prediction_data)

    # Explanations are optional; default to empty so the summary still prints
    # the predictions when they were not requested.
    explanations = result.get("explanations") or {}
    column_scores = explanations.get("top_column_scores") or []
    context_rows = explanations.get("top_relevant_context_rows") or []

    print("\nPrediction summary:")
    for query_idx, prediction in enumerate(predictions):
        api_row = query_row_positions[query_idx]

        # Each entry lists the top_k candidates for the target column, best
        # first. With top_k=1 there is a single candidate.
        candidates = ", ".join(
            f"{c['prediction']} (conf {c['confidence']:.2f})"
            for c in prediction[target_name]
        )
        print(
            f"\n  Query row {query_idx} (API row {api_row}): "
            f"{target_name} = {candidates}"
        )

        if column_scores:
            ranked = sorted(
                column_scores[query_idx].items(),
                key=lambda item: item[1],
                reverse=True,
            )
            influential = ", ".join(f"{name} {score:.2f}" for name, score in ranked)
            print(f"    Most influential columns: {influential}")

        if context_rows:
            print("    Most relevant context rows:")
            for row_idx in context_rows[query_idx]:
                # The index is a zero-based position into the full input table.
                print(f"      API row {row_idx}: {prediction_data['rows'][row_idx]}")


def get_access_token() -> str:
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


def make_prediction(
    access_token: str, prediction_data: dict, compress: bool = False
) -> dict:
    """
    Make a prediction request to the SAP GenAI Hub API for SAP RPT.

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

    if compress:
        import gzip

        encoded = gzip.compress(
            json.dumps(prediction_data).encode("utf-8"), compresslevel=1
        )
        headers["Content-Encoding"] = "gzip"
        response = requests.post(API_URL, headers=headers, data=encoded)
    else:
        response = requests.post(API_URL, headers=headers, json=prediction_data)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Prediction failed: {response.status_code} - {response.text}")


example_request_payload = {
    "index_column": "id",
    "prediction_config": {
        "target_columns": [
            {
                "name": "category",
                "prediction_placeholder": "?",
                "task_type": "classification",
                "top_k": 1,
            }
        ],
        # Request explanations in the response:
        # - top_column_scores returns the most influential feature columns per query row.
        # - top_relevant_context_rows returns row indices of the most relevant
        #   context rows per query row.
        #
        # IMPORTANT: each top_relevant_context_rows value is a zero-based,
        # sequential index into ALL rows sent to the API (payload["rows"] below).
        # It is not the "id" value and not an index into only the context rows.
        "explanations": {"top_column_scores": 4, "top_relevant_context_rows": 3},
    },
    "parse_data_types": True,
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


if __name__ == "__main__":
    # Step 1: Get access token
    print("Obtaining access token...")
    access_token = get_access_token()
    print("Access token obtained successfully!")

    # Step 2: Make prediction request
    payload = example_request_payload
    print_input_row_index(payload)
    result = make_prediction(access_token, payload, compress=True)
    print("\nPrediction successful!\n")
    print("Full Response:")
    print(json.dumps(result, indent=2))
    print_prediction_summary(result, payload)
