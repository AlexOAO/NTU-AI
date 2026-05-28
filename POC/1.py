from gradio_client import Client

c = Client('AlexOAO/asr-taiwanese')
print(c.view_api())