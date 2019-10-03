import os
import re
from datetime import datetime
from email.parser import Parser
from email.policy import default

import boto3

S3_BUCKET = os.getenv("S3_BUCKET")

MATCHERS = {"akr_airport_authority": {"from": r"akroncantonairport.com"}}


def get_match(msg):
    for slug, matcher in MATCHERS.items():
        for key, pattern in matcher.items():
            if re.search(pattern, msg.get(key, "")):
                return slug


def handler(event, context):
    s3 = boto3.client("s3")
    rec = event["Records"][0]
    rec_dt = datetime.strptime(rec["eventTime"], "%Y-%m-%dT%H:%M:%S.%fZ")

    obj_source = {"Bucket": S3_BUCKET, "Key": rec["s3"]["object"]["key"]}
    obj = s3.get_object(**obj_source)
    msg = Parser(policy=default).parsestr(obj["Body"].read().decode("utf-8"))

    match_slug = get_match(msg)
    if not match_slug:
        return

    s3.copy_object(
        CopySource=obj_source,
        Bucket=S3_BUCKET,
        Key=f"{match_slug}/{rec_dt.strftime('%Y/%m/%d/%H%M')}.eml",
    )
    s3.copy_object(
        CopySource=obj_source, Bucket=S3_BUCKET, Key=f"{match_slug}/latest.eml"
    )
