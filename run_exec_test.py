import sys, types
from pathlib import Path
p_candidates = [Path('app.py'), Path('emocare gpt/app.py'), Path('emocare gpt/emocare gpt/app.py')]
app_path = None
for p in p_candidates:
    if p.exists():
        app_path = p
        break
if app_path is None:
    raise SystemExit('app.py not found')
source = app_path.read_text(encoding='utf-8')
mod_name = '__loaded_app__'
mod = types.ModuleType(mod_name)
# Insert into sys.modules so dataclass references succeed
sys.modules[mod_name] = mod
mod.__file__ = str(app_path)
# Execute app.py into the module namespace
exec(compile(source, str(app_path), 'exec'), mod.__dict__)
# Call analyze_emotion
examples = [
    "teacher scolded me for scoring low in examinations",
    "my parents beated me",
    "they yelled at me",
    "i was beaten",
]
for s in examples:
    ins = mod.analyze_emotion(s)
    print('---')
    print('Input:', s)
    print('Emotion:', ins.emotion, 'Intensity:', ins.intensity, 'Confidence:', ins.confidence)
    print('Keywords:', ins.keywords)
