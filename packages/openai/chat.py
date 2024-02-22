#--web true
#--param OPENAI_API_KEY $OPENAI_API_KEY
#--param OPENAI_API_HOST $OPENAI_API_HOST

from openai import AzureOpenAI
import re
import socket
import requests
import json

ROLE = """
When requested to write code, pick Python.
When requested to show chess position, always use the FEN notation.
When showing HTML, always include what is in the body tag, 
but exclude the code surrounding the actual content. 
So exclude always BODY, HEAD and HTML .
"""

MODEL = "gpt-35-turbo"
AI = None

#cerca un dominio all'interno della stringa, e se' un nome di dominio valido lo restituisce
def get_domain(text):
    domain_regex = r'\b(?:https?://)?(?:www\.)?([a-z0-9-]+\.[a-z]{2,})(?:\b|$)'
    match = re.search(domain_regex, text)
    if match:
        return match.group(0)
    else:
        return None
    
def log_on_slack(msg):
    url = 'https://nuvolaris.dev/api/v1/web/utils/demo/slack'
    payload = {'text': msg}
    requests.post(url, json=payload)

def check_chess(text):
    check_text = r'\b(?:chess|scacchi)\b'
    match = re.search(check_text, text)
    return match

def get_chess_json():
    answer = requests.get('https://pychess.run.goorm.io/api/puzzle?limit=1')
    chess_dictionary = json.loads(answer.text)
    return chess_dictionary

def get_fen(gpt_answer):
    check_answer = r'^(?:yes|Yes)'
    if re.match(check_answer, gpt_answer):
        chess_json = get_chess_json()
        print(chess_json['items'][0]['fen'])
        log_on_slack(chess_json['items'][0]['puzzleid'])
    else:
        return

def req(msg):
    return [{"role": "system", "content": ROLE}, 
            {"role": "user", "content": msg}]

def ask(input):
    domain = get_domain(input)
    if  domain is not None:
        print(input)
        print(domain)
        ip_addr = socket.gethostbyname(domain)
        print(ip_addr)
        input = "Assuming " + domain + " has ip address " + ip_addr + ", answer this question: " + input
        log_on_slack(input)
    
    if check_chess(input):
        input = "is the following a request for a chess puzzle: " + input + ": answer only with yes or no,"

    comp = AI.chat.completions.create(model=MODEL, messages=req(input))
    if len(comp.choices) > 0:
        content = comp.choices[0].message.content
        return content
    return "ERROR"


"""
import re
from pathlib import Path
text = Path("util/test/chess.txt").read_text()
text = Path("util/test/html.txt").read_text()
text = Path("util/test/code.txt").read_text()
"""
def extract(text):
    res = {}

    # search for a chess position
    pattern = r'(([rnbqkpRNBQKP1-8]{1,8}/){7}[rnbqkpRNBQKP1-8]{1,8} [bw] (-|K?Q?k?q?) (-|[a-h][36]) \d+ \d+)'
    m = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    #print(m)
    if len(m) > 0:
        res['chess'] = m[0][0]
        return res

    # search for code
    pattern = r"```(\w+)\n(.*?)```"
    m = re.findall(pattern, text, re.DOTALL)
    if len(m) > 0:
        if m[0][0] == "html":
            html = m[0][1]
            # extract the body if any
            pattern = r"<body.*?>(.*?)</body>"
            m = re.findall(pattern, html, re.DOTALL)
            if m:
                html = m[0]
            res['html'] = html
            return res
        res['language'] = m[0][0]
        res['code'] = m[0][1]
        return res
    return res

def main(args):
    global AI
    (key, host) = (args["OPENAI_API_KEY"], args["OPENAI_API_HOST"])
    AI = AzureOpenAI(api_version="2023-12-01-preview", api_key=key, azure_endpoint=host)

    input = args.get("input", "")
    if input == "":
        res = {
            "output": "Welcome to the OpenAI demo chat",
            "title": "OpenAI Chat",
            "message": "You can chat with OpenAI."
        }
    else:
        output = ask(input)
        res = extract(output)
        res['output'] = output
        get_fen(output)

    return {"body": res }
