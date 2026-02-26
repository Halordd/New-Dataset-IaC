import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info("Received event for ERP forwarding: %s", json.dumps(event))

    # Placeholder for ERP integration (API call, queue push, etc.).
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "ERP forwarding simulated"})
    }
