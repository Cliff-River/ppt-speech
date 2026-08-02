# %%
import json

voices = []

with open("voices.json", "r") as f:
    voices = json.load(f)

[(i, item["ShortName"]) for i, item in enumerate(voices)]

# %%
print(len(voices))

# %%