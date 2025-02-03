import json

def get_message(category, code):
    with open("ai_config.json", "r", encoding="utf-8") as file:
        config = json.load(file)
    return config["messages"][category][code]
