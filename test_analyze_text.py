import importlib.util
from pathlib import Path

app_path = Path(__file__).parent / 'emocare gpt' / 'app.py'
# NOTE: the path above might be incorrect if running from project root; adjust to locate app.py
# Try multiple possible locations
candidates = [Path('app.py'), Path('emocare gpt/app.py'), Path('emocare gpt/emocare gpt/app.py')]
for p in candidates:
    if p.exists():
        app_path = p
        break

spec = importlib.util.spec_from_file_location('app', str(app_path))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

sentence = "teacher scolded me for scoring low in examinations"
insight = app.analyze_emotion(sentence)
print('Sentence:', sentence)
print('Result:', insight)
print('Emotion:', insight.emotion)
print('Intensity:', insight.intensity)
print('Confidence:', insight.confidence)
print('Keywords:', insight.keywords)
