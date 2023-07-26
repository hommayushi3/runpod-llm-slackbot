import json
import urllib.request
import urllib.parse
import os
from time import sleep

SLACK_TOKEN = os.getenv("SLACK_TOKEN")
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
SLACK_REPLIES_URL = "https://slack.com/api/conversations.replies"
RUNPOD_RUN_URL = "https://api.runpod.ai/v2/{}/run"
RUNPOD_STREAM_URL = "https://api.runpod.ai/v2/{}/stream/{}"
SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"

SLACK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0"
}

RUNPOD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0",
    "Authorization": f"Bearer {RUNPOD_API_KEY}"
}


def request(url, data, headers, is_json=False):
    if is_json:
        data = json.dumps(data).encode('utf-8')
    else:
        data = urllib.parse.urlencode(data).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req) as response:
        # Read the response
        raw_response = response.read()
    
        # Convert the response to JSON
        json_response = json.loads(raw_response.decode())
        return json_response
    
    
def format_prompt(chat_history, prompt_format={}):
    """Expect prefix,, user_prefix, bot_prefix, sep"""
    prompt = prompt_format.get("prefix", "")
    user_prefix = prompt_format.get("user_prefix", "USER: ")
    bot_prefix = prompt_format.get("bot_prefix", "ASSISTANT: ")
    sep = prompt_format.get("sep", " ")
    
    for message in chat_history:
        if "bot_id" in message:
            role = bot_prefix
        else:
            role = user_prefix
            message["text"] = message["text"].strip().split(maxsplit=1)[1]
            
        prompt += role + message["text"] + sep
        
    prompt += bot_prefix
    return prompt
    

def lambda_handler(event, context):
    endpoint_id = event["RUNPOD_ENDPOINT_ID"]
    prompt_format = event.get("PROMPT_FORMAT", {})
    event = json.loads(event["body"])["event"]
    
    # get thread_ts (or ts if first message)
    ts = event.get("thread_ts", event["ts"])
    channel = event["channel"]
    # get thread replies
    slack_thread_data = {
        "ts": ts,
        "channel": channel,
        "token": SLACK_TOKEN
    }
    chat_history = request(
        SLACK_REPLIES_URL, data=slack_thread_data, headers=SLACK_HEADERS
    ).get("messages", [event])
    
    # format prompt
    prompt = format_prompt(chat_history, prompt_format)
    print(prompt)
    
    # run prompt. Edit these parameters to change generation behavior.
    generation_input = {
        'max_new_tokens': 1800,
        'temperature': 0.3,
        'top_k': 50,
        'top_p': 0.7,
        'repetition_penalty': 1.2,  
        'stop_tokens': ["</s>"]
    }
    generation_input["prompt"] = prompt
    prompt_response = request(
        RUNPOD_RUN_URL.format(endpoint_id),
        data={"input": generation_input},
        headers=RUNPOD_HEADERS,
        is_json=True
    )
    print(prompt_response)
    task_id = prompt_response["id"]
    runpod_stream_url = RUNPOD_STREAM_URL.format(endpoint_id, task_id)
    
    # wait for prompt
    while True:
        stream_response = request(
            runpod_stream_url, data={}, headers=RUNPOD_HEADERS, is_json=True
        )
        if "stream" in stream_response and len(stream_response["stream"]) > 0:
            print(stream_response["stream"])
            slack_thread_data["text"] = stream_response["stream"][0][
                "output"
            ].split('</s>', maxsplit=1)[0]
            break
                
        sleep(1)
        
    slack_thread_data["thread_ts"] = slack_thread_data["ts"]
    # send reply back to slack
    return request(
        SLACK_POST_MESSAGE_URL,
        data=slack_thread_data,
        headers=SLACK_HEADERS
    )

