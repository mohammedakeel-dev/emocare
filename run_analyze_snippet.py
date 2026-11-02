import importlib.util
from pathlib import Path

# find app.py
candidates = [Path('app.py'), Path('emocare gpt/app.py'), Path('emocare gpt/emocare gpt/app.py')]
app_path = None
for p in candidates:
    if p.exists():
        app_path = p
        break
if app_path is None:
    raise SystemExit('app.py not found')

spec = importlib.util.spec_from_file_location('app_mod', str(app_path))
app_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_mod)

examples = [
    "teacher scolded me for scoring low in examinations",
    "my parents beated me",
    "they yelled at me",
    "i was beaten",
]
for s in examples:
    ins = app_mod.analyze_emotion(s)
    print('---')
    print('Input:', s)
    print('Emotion:', ins.emotion, 'Intensity:', ins.intensity, 'Confidence:', ins.confidence)
    print('Keywords:', ins.keywords)
