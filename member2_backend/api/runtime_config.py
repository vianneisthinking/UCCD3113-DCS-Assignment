"""Load optional deployment configuration before importing the application."""

import os


def load_ssm_parameters():
    prefix = os.getenv("CONFIG_PARAMETER_PREFIX", "").strip()
    if not prefix:
        return

    import boto3

    client = boto3.client("ssm", region_name=os.getenv("AWS_REGION"))
    next_token = None
    while True:
        request = {
            "Path": prefix.rstrip("/") + "/",
            "Recursive": False,
            "WithDecryption": True,
        }
        if next_token:
            request["NextToken"] = next_token
        response = client.get_parameters_by_path(**request)
        for parameter in response.get("Parameters", []):
            name = parameter["Name"].rsplit("/", 1)[-1]
            os.environ.setdefault(name, parameter["Value"])
        next_token = response.get("NextToken")
        if not next_token:
            break
