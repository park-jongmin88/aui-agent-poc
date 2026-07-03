def predict(payload):
    """Template prediction hook. Replace with real sklearn inference."""
    return {
        "sample": "sklearn",
        "received": payload,
        "prediction": "replace_with_model_output",
    }
