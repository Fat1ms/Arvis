from config.config import Config

c = Config()
print(f"default_engine: {c.get('tts.default_engine')}")
print(f"voice: {c.get('tts.voice')}")
print(f"bark.voice: {c.get('tts.bark.voice')}")
