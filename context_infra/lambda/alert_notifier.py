import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sns = boto3.client("sns")
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]


def lambda_handler(event, context):
    logger.info("Received event for alerting: %s", json.dumps(event))

    response = sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject="Monitron anomaly event",
        Message=json.dumps(event, ensure_ascii=False),
    )

    return {
        "statusCode": 200,
        "body": json.dumps(
            {"message": "Alert sent", "message_id": response["MessageId"]}
        ),
    }
