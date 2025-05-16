from datetime import datetime
import json
import os
import re
import requests
import sys

import streamlit as st

import azure.cognitiveservices.speech as speechsdk

from openai import AzureOpenAI

endpoint    = os.environ.get("AZURE_OPENAI_ENDPOINT", "https://api.openai.azure.com/")
deployment  = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "deployment-name")
model_name  = os.environ.get("AZURE_OPENAI_MODEL_NAME", "model-name")
api_key     = os.environ.get("AZURE_OPENAI_API_KEY", "")
api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

search_endpoint  = os.environ.get("AZURE_SEARCH_ENDPOINT", "https://api.search.azure.com/")
search_index     = os.environ.get("AZURE_SEARCH_INDEX", "index-name")
search_type      = os.environ.get("AZURE_SEARCH_TYPE", "query-type")
semantic_config  = os.environ.get("AZURE_SEARCH_SEMANTIC_CONFIG", "")
embed_deployment = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "embedding-deployment-name")

speech_key    = os.environ.get("AZURE_SPEECH_KEY", "your-speech-key")
speech_region = os.environ.get("AZURE_SPEECH_REGION", "your-speech-region")

swoop_ve_endpoint  = os.environ.get("SWOOP_VE_ENDPOINT", "https://swoop.swoopanalytics.com/")
swoop_ve_key       = os.environ.get("SWOOP_VE_KEY",      "")
swoop_sp_endpoint  = os.environ.get("SWOOP_SP_ENDPOINT", "https://swoop-sharepoint.swoopanalytics.com/")
swoop_sp_key       = os.environ.get("SWOOP_SP_KEY",      "")

http_proxy  = os.environ.get("HTTP_PROXY", None)

client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=api_key,
)

speech_config = speechsdk.SpeechConfig(speech_key, region=speech_region)
audio_output_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)

speech_config.speech_recognition_language="en-US"
speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

speech_config.speech_synthesis_voice_name='en-US-JennyMultilingualNeural'
speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_output_config)
tts_sentence_end = [ ".", "!", "?", ";", "。", "！", "？", "；", "\n" ]

def tool_current_date():
    """ Return the current date in the format YYYY-MM-DD"""
    return "The current date is " + datetime.today().strftime('%Y-%m-%d')

def tool_yammer_get_user_id(name):
    """ Get the user ID from the name"""
    try:
        encoded_name = name.replace(" ", "%20")
        url = swoop_ve_endpoint + f"v1/api/Enterprise/GetUserID?Name={encoded_name}"
        response = requests.get(url, headers={"Authorization": f"Bearer {swoop_ve_key}"}, proxies={"http": http_proxy, "https": http_proxy}, verify=False)

        response = response.json()
        if response["Success"] == "TRUE":
            return name + " has the user id of " + response["Result"]
        else:
            return name + " does not exist in the system."
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")


def tool_yammer_key_stats(mode, modeID, dateFrom, dateTo):
    """ Get the posts, replies, likes, mentions and notifications from Viva Engage for the company"""
    try:
        url = swoop_ve_endpoint + f"v1/api/{mode}/KeyStats?DateFrom={dateFrom}&DateTo={dateTo}&ModeID={modeID}"
        response = requests.get(url, headers={"Authorization": f"Bearer {swoop_ve_key}"}, proxies={"http": http_proxy, "https": http_proxy}, verify=False)

        response = response.json()
        if response["Success"] == "TRUE":
            result = f"The Viva Engage key statistics are in json {response['Result']}"
            return result
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")

def tool_sharepoint_get_user_id(name):
    """ Get the user ID from the name"""
    try:
        encoded_name = name.replace(" ", "%20")
        url = swoop_sp_endpoint + f"v1/api/Enterprise/GetUserID?Name={encoded_name}"
        response = requests.get(url, headers={"Authorization": f"Bearer {swoop_sp_key}"}, proxies={"http": http_proxy, "https": http_proxy}, verify=False)

        response = response.json()
        if response["Success"] == "TRUE":
            return name + " has the user id of " + response["Result"]
        else:
            return name + " does not exist in the system."
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")

def tool_sharepoint_key_stats(mode, modeID, dateFrom, dateTo):
    """ Get the views, visits, visitors and average time on page from SharePoint for the company"""
    try:
        url = swoop_sp_endpoint + f"v1/api/{mode}/SharePoint_KeyStats?DateFrom={dateFrom}&DateTo={dateTo}&ModeID={modeID}"
        response = requests.get(url, headers={"Authorization": f"Bearer {swoop_sp_key}"}, proxies={"http": http_proxy, "https": http_proxy}, verify=False)

        response = response.json()
        if response["Success"] == "TRUE":
            result = f"The SharePoint key statistics are in json {response['Result']}"
            return result
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")

def converse(question):
    messages=[]
    for m in st.session_state.messages:
        if m["role"] != "user" and m["role"] != "tool":
            messages.append({"role": m["role"], "content": m["content"]})

    messages.append({"role": "user", "content": question})
    st.session_state.messages.append({"role": "user", "content": question})
    send_message(messages)

def send_message(messages, calls=None):
    print("Sending message...")
    if calls is None:
        calls = {}

    tool_choice = "auto"
    for c in calls:
        if calls[c] > 10:
            tool_choice = "none"
            break

    answer = client.chat.completions.create(
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "tool_current_date",
                    "description": "Get the current date in the format YYYY-MM-DD"
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "tool_yammer_get_user_id",
                    "description": "Get the user ID from the name in Viva Engage",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "The name of the user."
                            },
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "tool_yammer_key_stats",
                    "description": "Get the posts, replies, likes, mentions and notifications from Viva Engage",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "mode": {
                                "type": "string",
                                "description": "Use the mode Personal for a user's statistics and Enterprise for the company's statistics.",
                                "enum": ["Personal", "Enterprise"]
                            },
                            "modeID": {
                                "type": "string",
                                "description": "Must be empty when using Enterprise mode. And must the ID of the user when using Personal mode."
                            },
                            "dateFrom": {
                                "type": "string",
                                "description": "The from date in the format YYYY-MM-DD"
                            },
                            "dateTo": {
                                "type": "string",
                                "description": "The to date in the format YYYY-MM-DD"
                            }
                        },
                        "required": ["mode", "modeID", "dateFrom", "dateTo"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "tool_sharepoint_get_user_id",
                    "description": "Get the user ID from the name in SharePoint",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "The name of the user."
                            },
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "tool_sharepoint_key_stats",
                    "description": "Get the views, visits, visitors for SharePoint",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "mode": {
                                "type": "string",
                                "description": "Use the mode Personal for a user's statistics and Enterprise for the company's statistics.",
                                "enum": ["Personal", "Enterprise"]
                            },
                            "modeID": {
                                "type": "string",
                                "description": "Must be empty when using Enterprise mode. And must the ID of the user when using Personal mode."
                            },
                            "dateFrom": {
                                "type": "string",
                                "description": "The from date in the format YYYY-MM-DD"
                            },
                            "dateTo": {
                                "type": "string",
                                "description": "The to date in the format YYYY-MM-DD"
                            }
                        },
                        "required": ["mode", "modeID", "dateFrom", "dateTo"]
                    }
                }
            }
        ],
        extra_body={
            "data_sources": [
                {
                    "type": "azure_search",
                    "parameters": {
                        "endpoint": search_endpoint,
                        "index_name": search_index,
                        "authentication": { "type": "system_assigned_managed_identity" },
                        "semantic_configuration": semantic_config,
                        "query_type": search_type,
                        "embedding_dependency": {
                            "deployment_name": embed_deployment,
                            "type": "deployment_name"
                        },
                        "fields_mapping": {
                            "content_fields_separator": "\\n",
                            "content_fields": ["chunk"],
                            "title_field": "custom_title",
                            "url_field": "custom_url",
                            "vector_fields": ["vector"]
                        }
                    }
                }
            ]
        },
        messages=messages,
        model=deployment,
        tool_choice=tool_choice
    )


    response = answer.choices[0].message
    if response.content:
        messages.append({"role": response.role, "content": response.content})
        st.session_state.messages.append({"role": response.role, "content": response.content})

    if response.tool_calls:
        intent = ""
        if hasattr(response, "intent") and response.intent[0]:
            intent = response.intent[0]

        for tool_call in response.tool_calls:
            if tool_call.function.name not in calls:
                calls[tool_call.function.name] = 0

            calls[tool_call.function.name] += 1
            if calls[tool_call.function.name] < 10:
                if tool_call.function.name == "tool_current_date":
                    result = tool_current_date()
                elif tool_call.function.name == "tool_yammer_get_user_id":
                    func_args = tool_call.function.arguments
                    func_args = json.loads(func_args)
                    result = tool_yammer_get_user_id(func_args["name"])
                elif tool_call.function.name == "tool_yammer_key_stats":
                    func_args = tool_call.function.arguments
                    func_args = json.loads(func_args)
                    result = tool_yammer_key_stats(func_args["mode"], func_args["modeID"], func_args["dateFrom"], func_args["dateTo"])
                elif tool_call.function.name == "tool_sharepoint_get_user_id":
                    func_args = tool_call.function.arguments
                    func_args = json.loads(func_args)
                    result = tool_sharepoint_get_user_id(func_args["name"])
                elif tool_call.function.name == "tool_sharepoint_key_stats":
                    func_args = tool_call.function.arguments
                    func_args = json.loads(func_args)
                    result = tool_sharepoint_key_stats(func_args["mode"], func_args["modeID"], func_args["dateFrom"], func_args["dateTo"])

                tool_response = {
                    "role": "tool",
                    "content": f"{intent} {result}",
                }

                updated = False
                for k,m in enumerate(messages):
                    if m["role"] == "tool" and m["tool_call_id"] == tool_call.function.name:
                        updated = True
                        messages[k]["content"] = f"{intent} {result}"


                if updated == False:
                    messages.append({
                        "tool_call_id": tool_call.function.name,
                        "role": "tool",
                        "content": f"{intent} {result}",
                    })
                print(f"Tool call: {tool_call.function.name}")
                print(tool_call)
                print(result)
                st.session_state.messages.append(tool_response)

        send_message(messages, calls)

def new_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.messages.append({"role": "system", "content": """\
Introduction:
- You are \"Dr SWOOP\" and you act as a coach to help people improve communication and collaboration.
- Your responses must always come from the sources you have been given. Do not answer questions unless based on the sources. Only include references to sources that are verified and accessible. If you do not have a source, state that explicitly.
- Use examples from sources to illustrate key points.
- Use the goals and benchmark data listed in \"2024/2025 Enterprise Level Goals across SWOOP products\" to provide guidance on metrics, goals and averages, but don't reference this source in your response.
- If you are uncertain about a question, reply with \"Hmm, I am not sure.\".

Product Naming:
- Always refer to Microsoft's product as \"Viva Engage\" instead of \"Yammer\". Yammer is the previous name for Viva Engage, but this is not used anymore.
- Clarify if asked about \"SWOOP for Teams\", \"SWOOP for Viva Engage\", \"SWOOP for M365\" or \"SWOOP for SharePoint\"
- \"SWOOP\", \"Swoop\" and \"swoop\" is the same, but always use SWOOP (all upper-case) when you answer.

Product-Specific Information:
- Provide examples in each response, and examples must be based on the sources.
- If discussing SWOOP for SharePoint, emphasise its relation to SharePoint as an intranet.
- Provide links to support articles, blog posts or case studies from the sources you have been provided.
- Do not provide links to sources that do not exist.
- The link to the SWOOP Support Portal is https://support.swoopanalytics.com
- The link to the SWOOP website is https://www.swoopanalytics.com
- SWOOP case studies can be found on the SWOOP website is https://www.swoopanalytics.com/case-studies
- SWOOP benchmarking reports can be found on the SWOOP website https://www.swoopanalytics.com
- SWOOP blogposts can be found on the SWOOP website https://www.swoopanalytics.com/blog
- The SWOOP Users and Friends group on LinkedIn can be accessed at https://www.linkedin.com/groups/14114594/
- The term \"Influencer Report\" is not used in SWOOP for Viva Engage; instead, the relevant report is called the Influential People report.


Engagement:
- If you are being asked about engagement, then it means engagement score.

Individuals and Privacy:
- You can mention names of organisations, companies and job titles of people, but do not mention names of people.
- SWOOP Analytics' privacy policy can be found at https://www.swoopanalytics.com/privacy
- SWOOP Analytics' Trust Centre includes information about data security, privacy, penetration testing and information security can be found at https://trust.swoopanalytics.com

Character Maintenance:
- Maintain the persona of \"Dr SWOOP\" without breaking character.

Tools:
- If you need to know the current date, please use the tool_current_date function.
- Please check you have the data to answer the question before you call any tools or functions.
- If you are unsure of the users id for Viva Engage, please use the tool_yammer_get_user_id function.
- When a user asks for key statistics for Viva Engage, you should call the tool_yammer_key_stats function.
- If you are unsure of the users id in SharePoint, please use the tool_sharepoint_get_user_id function.
- When a user asks for key statistics for SharePoint, you should call the tool_sharepoint_key_stats function.
"""
})
        st.session_state.messages.append({"role": "assistant", "content": "Hello! I am Dr SWOOP, your AI assistant. I have read all of SWOOP Analytics' published insights, case studies, support articles and blog posts. Ask me anything you like and I'll try to help out."})

def get_mic_input():
    question = start_listening()
    if question is not None:
        converse(question)

def start_listening():
    st.session_state.button = True
    user_input = None
    print("Listening...")
    try:
        result = speech_recognizer.recognize_once_async().get()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            if result.text == "Stop.":
                print("Stopping...")
            else:
                print(f"Recognized: {result.text}")
                user_input = result.text
        elif result.reason == speechsdk.ResultReason.NoMatch:
            print("No speech could be recognized")
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            print(f"Speech Recognition canceled: {cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print(f"Error {cancellation_details.error_details}")
    except KeyboardInterrupt:
        speechsdk.SpeechSynthesizer.stop_speaking_async()

    st.session_state.button = False
    return user_input


st.title("DrNoSWOOP")
st.markdown(
"""
<style>
#MainMenu {visibility: hidden;}
.stAppDeployButton {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

if "model" not in st.session_state:
    st.session_state["model"] = model_name

if "button" not in st.session_state:
    st.session_state["button"] = False

new_session()

st.button("Start Listening", on_click=get_mic_input, disabled=st.session_state.button)
if question := st.chat_input():
    converse(question)

for message in st.session_state.messages:
    if message["role"] != "system" and message["role"] != "tool":
        with st.chat_message(message["role"]):
            st.markdown(re.sub(r'\[(.*?)\]', r'', message["content"]))


