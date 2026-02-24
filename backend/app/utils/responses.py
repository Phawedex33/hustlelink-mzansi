from flask import g, jsonify


def error_response(message, status_code, code):
    """
    Standardized error response format for the API.
    """
    return (
        jsonify(
            {
                "msg": message,
                "error": {
                    "code": code,
                    "message": message,
                    "request_id": getattr(g, "request_id", ""),
                },
            }
        ),
        status_code,
    )
