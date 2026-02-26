import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info("PII audit event received: %s", json.dumps(event))

    # Placeholder for SIEM/SOC forwarding.
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "PII audit forwarding simulated"}),
    }
