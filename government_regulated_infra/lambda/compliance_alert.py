import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sns = boto3.client("sns")
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]


def lambda_handler(event, context):
    logger.info("Compliance event received: %s", json.dumps(event))

    response = sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject="Regulated data compliance alert",
        Message=json.dumps(event, ensure_ascii=False),
    )

    return {
        "statusCode": 200,
        "body": json.dumps(
            {"message": "Compliance alert sent", "message_id": response["MessageId"]}
        ),
    }
