import sys, os
sys.path.insert(0, r'c:\Users\Hp\OneDrive\Desktop\emocare gpt\emocare gpt\emocare gpt')
import app
from pathlib import Path

uploads = Path(app.UPLOADS_DIR)
if not uploads.exists():
    print('uploads folder missing:', uploads)
    sys.exit(1)

for f in sorted(uploads.iterdir()):
    if f.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.bmp'):
        continue
    try:
        res = app.analyze_image_emotion(str(f))
        print(f.name, '->', res.emotion, res.intensity, f'{res.confidence:.2f}')
    except Exception as e:
        print(f.name, '-> ERROR', e)
