import sys, os, importlib
sys.path.insert(0, r'c:\Users\Hp\OneDrive\Desktop\emocare gpt\emocare gpt\emocare gpt')
import app

p = os.path.join(str(app.UPLOADS_DIR), 'happy.jpeg')
if not os.path.exists(p):
    ul = str(app.UPLOADS_DIR)
    print('No happy.jpeg found at', p)
    if os.path.exists(ul):
        files = os.listdir(ul)
        print('uploads contains:', files)
        if files:
            p = os.path.join(ul, files[0])
            print('Using', p, 'for test')
            # run analysis on the selected file
            res = app.analyze_image_emotion(p)
            print('Result:', res.emotion, res.intensity, res.confidence, res.keywords)
            print('Wrote diagnostic entries to image_emotion.log (if any)')
    else:
        print('uploads folder missing at', ul)
else:
    res = app.analyze_image_emotion(p)
    print('Result:', res.emotion, res.intensity, res.confidence, res.keywords)
    print('Wrote diagnostic entries to image_emotion.log (if any)')
