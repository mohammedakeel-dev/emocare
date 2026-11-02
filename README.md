# EmoCare

A privacy-first emotional support companion that blends keyword-aware NLP, TextBlob sentiment, and (future) real-time facial cues to deliver empathetic replies, activity nudges, and weekly reflections—all stored locally for confidentiality.

## Getting started

1. **Create a virtual environment (optional)**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
2. **Install dependencies**
   ```powershell
   pip install -r requirements.txt
   ```
3. **Run the app**
   ```powershell
   python app.py
   ```
4. Visit `http://127.0.0.1:5000` to sign up and log in. Credentials are stored in `emocare.db` (SQLite) inside the project folder.

Environment variable `EMOCARE_SECRET_KEY` can be set for production-grade sessions. TextBlob ships with the pattern analyzer it needs, but if you see missing corpora warnings, run `python -m textblob.download_corpora`.

## Features

- **Emotion-aware chat:** `/chat` analyzes every message with TextBlob polarity + keyword cues, replies in a human tone, and logs both sides (emotion + intensity) into SQLite.
- **Day-level storage:** Conversations are grouped per day; the dashboard, activities, and history pages all read from the same local database.
- **Auto analytics:** Chart.js visualizations pull real interaction data for the last seven days, showing both timelines and distribution.
- **Daily reflection files:** Each day you chat, a plaintext summary is written to `reports/YYYY-MM-DD_user-<id>.txt`. Download links are available on the dashboard and the reports page.
- **Contextual activities:** Recommendations adapt to your latest logged emotion so you always get relevant rituals.
- **History + reports:** Dedicated pages let you browse previous conversations and regenerate reports for any date.

## Flowchart

See `docs/flowchart.md` for a Mermaid diagram that illustrates how text + facial emotion detection feeds into dialogue, analytics, and activity recommendations.

## Next steps

- Add encryption-at-rest for `emocare.db` plus optional passcode-unlock.
- Integrate multilingual NLP and on-device face-emotion detection.
- Expand the chat composer with real media uploads + camera streaming.
- Layer in push/email reminders and configurable daily moods.
