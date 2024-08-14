import pulumi
import pulumi_aws as aws


lambda_role = aws.iam.Role('lambda-execution-role',
    assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": "sts:AssumeRole",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Effect": "Allow",
                "Sid": ""
            }
        ]
    }"""
)

aws.iam.RolePolicyAttachment('lambda-basic-execution',
    role=lambda_role.name,
    policy_arn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
)

lambda_function_code = """
import random
import json

def lambda_handler(event, context):
    names = ['Alice', 'Moe', 'Snowflake', 'Diana', 'Eve', 'Cheese']
    name = random.choice(names)

    return {
        'statusCode': 200,
        'body': json.dumps(f'Hello World, {name}')
    }
"""

lambda_function = aws.lambda_.Function('crossplane-lambda-function',
    role=lambda_role.arn,
    runtime='python3.8',
    handler='index.lambda_handler',
    code=pulumi.AssetArchive({
        'index.py': pulumi.StringAsset(lambda_function_code)
    })
)


api = aws.apigateway.RestApi('api-gateway',
    description="API Gateway for Lambda function",
)


resource = aws.apigateway.Resource('api-gateway-resource',
    rest_api=api.id,
    parent_id=api.root_resource_id,
    path_part="lambda"
)


method = aws.apigateway.Method('api-gateway-method',
    rest_api=api.id,
    resource_id=resource.id,
    http_method="POST",
    authorization="NONE"
)

integration = aws.apigateway.Integration('api-gateway-integration',
    rest_api=api.id,
    resource_id=resource.id,
    http_method=method.http_method,
    integration_http_method="POST",
    type="AWS_PROXY",
    uri=lambda_function.invoke_arn
)


method_response = aws.apigateway.MethodResponse('method-response',
    rest_api=api.id,
    resource_id=resource.id,
    http_method=method.http_method,
    status_code="200",
    response_models={
        "application/json": "Empty"
    }
)

# Integration response setup
integration_response = aws.apigateway.IntegrationResponse('integration-response',
    rest_api=api.id,
    resource_id=resource.id,
    http_method=method.http_method,
    status_code=method_response.status_code,
    response_templates={
        "application/json": ""
    }
)

deployment = aws.apigateway.Deployment('api-gateway-deployment',
    rest_api=api.id,
    stage_name="dev",
    opts=pulumi.ResourceOptions(depends_on=[method, integration])
)

lambda_permission = aws.lambda_.Permission('lambda-permission',
    action="lambda:InvokeFunction",
    function=lambda_function.name,
    principal="apigateway.amazonaws.com",
    source_arn=deployment.execution_arn.apply(lambda arn: arn + "/*/*")
)

pulumi.export('url', deployment.invoke_url.apply(lambda url: url + '/lambda'))
pulumi.export('lambda_arn', lambda_function.arn)