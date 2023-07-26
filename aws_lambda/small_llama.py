import boto3
import json
import logging

lam = boto3.client('lambda')
RUNPOD_ENDPOINT_ID = "" # Enter in your RunPod endpoint ID here.

def lambda_handler(event, context):
    event["RUNPOD_ENDPOINT_ID"] = RUNPOD_ENDPOINT_ID
    # Edit the prompt format to reflect the expected format for your LLM
    event["PROMPT_FORMAT"] = {
        "prefix": """<|system|>You are an AI assistant that follows instruction extremely well.
Help as much as you can.</s>""",
        "user_prefix": "<|prompter|>",
        "bot_prefix": "<|assistant|>",
        "sep": "</s>"
    }
    lam.invoke(
        FunctionName='slackbot_postmessage',
        InvocationType='Event',
        Payload=json.dumps(event)
    )
    return {
        'statusCode': 200,
        'body': json.loads(event.get('body', {})).get('challenge', 'OK')
    }
