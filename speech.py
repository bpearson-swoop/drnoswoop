import os
import sys

import streamlit as st

from openai import AzureOpenAI

import azure.cognitiveservices.speech as speechsdk

endpoint    = os.environ.get("AZURE_OPENAI_ENDPOINT", "https://api.openai.azure.com/")
deployment  = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "deployment-name")
model_name  = os.environ.get("AZURE_OPENAI_MODEL_NAME", "model-name")
api_key     = os.environ.get("AZURE_OPENAI_API_KEY", "your-subscription-key")
api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

search_endpoint  = os.environ.get("AZURE_SEARCH_ENDPOINT", "https://api.search.azure.com/")
search_index     = os.environ.get("AZURE_SEARCH_INDEX", "index-name")
search_type      = os.environ.get("AZURE_SEARCH_TYPE", "query-type")
semantic_config  = os.environ.get("AZURE_SEARCH_SEMANTIC_CONFIG", "")
embed_deployment = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "embedding-deployment-name")

speech_key    = os.environ.get("AZURE_SPEECH_KEY", "your-speech-key")
speech_region = os.environ.get("AZURE_SPEECH_REGION", "your-speech-region")

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

def ask(prompt):
    response = client.chat.completions.create(
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
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        model=deployment,
        stream=True
    )

    collected=[]
    last = None
    try:
        for chunk in response:
            if len(chunk.choices) > 0:
                chunk_message = chunk.choices[0].delta.content
                if chunk_message is not None:
                    collected.append(chunk_message)
                    if chunk_message in tts_sentence_end:
                        text = "".join(collected).strip()
                        if text != '':
                            print(f"Speech Synthesis: {text}")
                            last = speech_synthesizer.speak_text_async(text)
                            collected.clear()
    except KeyboardInterrupt:
        speech_synthesizer.stop_speaking_async()

    if last:
        last.get()

def chat():
    while True:
        print("Listening...")
        try:
            result = speech_recognizer.recognize_once_async().get()

            print(result)
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                if result.text == "Stop.":
                    print("Stopping...")
                    break

                print(f"Recognized: {result.text}")
                ask(result.text)
            elif result.reason == speechsdk.ResultReason.NoMatch:
                print("No speech could be recognized")
                break
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                print(f"Speech Recognition canceled: {cancellation_details.reason}")
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    print(f"Error {cancellation_details.error_details}")
        except KeyboardInterrupt:
            speechsdk.SpeechSynthesizer.stop_speaking_async()
            break
        except EOFError:
            break

try:
    chat()
except KeyboardInterrupt:
    speechsdk.SpeechSynthesizer.stop_speaking_async()
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
