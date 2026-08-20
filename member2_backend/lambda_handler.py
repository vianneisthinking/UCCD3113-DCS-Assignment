"""AWS Lambda entry point for API Gateway HTTP API v2."""

from api.runtime_config import load_ssm_parameters

load_ssm_parameters()

from mangum import Mangum

from api.main import app


handler = Mangum(app, lifespan="off")
