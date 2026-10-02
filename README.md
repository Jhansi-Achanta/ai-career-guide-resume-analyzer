# AI Career Guide & Resume Analyzer

A student-friendly web app built with **Flask + vanilla JavaScript + Google Gemini**.

It has two tools:

1. **AI Career Guide** - you describe your education, skills, interests, target role and how
   much time you can study each day, and Gemini designs a career plan with a **30-day
   learning schedule**, resources, projects and interview preparation.
2. **Resume Analyzer** - you upload a **PDF or DOCX** resume plus a **target job role**, and
   Gemini scores it the way an Applicant Tracking System (ATS) would, showing missing
   skills, missing keywords, certification ideas and exactly what to fix.

---

## Features

### AI Career Guide
- Career guidance and a summary of where you stand today
- Recommended roles with entry level and growth path
- Recommended skills (technical + soft) with priorities
- Ordered learning priorities with estimated hours
- **30-day learning plan** split into time blocks with tasks and deliverables
- Free learning resources with real URLs
- Project suggestions to build a portfolio
- Career preparation and interview preparation tips

### Resume Analyzer
- **ATS score out of 100** with a category-by-category breakdown
- Resume summary
- Detected skills
- Missing skills (with why it matters + priority)
- Missing ATS keywords
- Certification suggestions
- Project improvement suggestions
- Formatting and content improvement suggestions
- **Target-role comparison** with a match percentage, strengths and gaps
- Job portal suggestions

### Everywhere
- Pale pink + sky-blue responsive theme, works on mobile
- History page: every report and plan is saved to JSON and can be reopened or deleted
- Friendly error messages for bad files, empty resumes and Gemini API problems
- The API key **never** reaches the browser

---

## Tech stack

| Layer     | Technology                                        |
|-----------|---------------------------------------------------|
| Frontend  | HTML, CSS, vanilla JavaScript (no frameworks, no build step) |
| Backend   | Python 3 + Flask                                  |
| Storage   | JSON files in the `data/` folder                  |
| AI        | Google Gemini API via the `google-genai` SDK      |
| Secrets   | `python-dotenv` reading a `.env` file             |

---

## Project structure

```
1000 coders/
├── app.py                     Flask app: JSON API + serves the frontend pages
├── config.py                  Loads .env, exposes the model name, paths and limits
├── requirements.txt           Python dependencies
├── .env                       YOUR SECRET Gemini API key (never commit this)
├── .env.example               Safe template showing the required variable names
├── .gitignore                 Ignores .env, __pycache__ and the generated data files
├── README.md                  This file
│
├── services/
│   ├── __init__.py
│   ├── gemini_client.py       Talks to Gemini: retries, JSON parsing, friendly errors
│   ├── prompts.py             System prompts + JSON schemas for both features
│   └── resume_parser.py       PDF (PyPDF2) / DOCX (python-docx) -> plain text
│
├── storage/
│   ├── __init__.py
│   ├── json_store.py          Atomic, thread-safe JSON read/write helpers
│   └── records.py             Save / list / get / delete analyses and career plans
│
├── data/
│   ├── analyses.json          Saved resume reports (created automatically)
│   └── career_plans.json      Saved career plans (created automatically)
│
├── static/
│   ├── index.html             Landing page
│   ├── career.html            AI Career Guide form + results
│   ├── analyzer.html          Resume Analyzer upload form + results
│   ├── history.html           Saved reports and plans
│   ├── css/style.css          The whole pale-pink / sky-blue theme
│   └── js/
│       ├── api.js             Shared fetch helpers, alerts, health banner
│       ├── render.js          Turns saved JSON into the HTML result sections
│       ├── career.js          Career Guide page logic
│       ├── analyzer.js        Resume Analyzer page logic
│       └── history.js         History page logic
│
└── tests/
    ├── __init__.py
    └── test_api.py            19 tests: API behaviour + resume parsing (no API key needed)
```

---

## Setup (3 steps)

### 1. Install the dependencies

```powershell
python -m pip install -r requirements.txt
```

### 2. Add your Gemini API key

Get a free key from <https://aistudio.google.com/apikey>, then open the `.env` file
in the project folder and paste it after the `=` sign:

```ini
GEMINI_API_KEY=AIza...your_real_key_here
GEMINI_MODEL=gemini-3.8-flash
```

> `.env` is listed in `.gitignore`, so your key is never committed.
> `.env.example` is the safe, shareable template.
> Use `/api/models` (see below) if you ever need to check which models your key can use.

### 3. Run the app

```powershell
python app.py
```

Then open **<http://127.0.0.1:5000>** in your browser.

```
======================================================================
  AI Career Guide & Resume Analyzer
  Open http://127.0.0.1:5000 in your browser
  Gemini model : gemini-3.8-flash
  Data folder  : ...\1000 coders\data
======================================================================
```

If the key is missing the app still starts and shows a banner telling you what to add,
instead of crashing.

---

## Running the tests

The tests mock Gemini, so **no API key and no network quota are needed**. They write to a
temporary folder, so your real `data/*.json` files are untouched.

```powershell
python -m unittest tests.test_api -v
```

Expected result: `Ran 19 tests ... OK`

---

## API reference

Everything the frontend uses. All responses are JSON.

| Method   | Endpoint                        | Purpose                                        |
|----------|---------------------------------|------------------------------------------------|
| `GET`    | `/api/health`                   | Status, whether the key is set, upload limits  |
| `GET`    | `/api/target-roles`             | Role + experience-level suggestions            |
| `GET`    | `/api/models`                   | Which Gemini models your key can use           |
| `POST`   | `/api/career/plan`              | Generate a career plan (JSON body)             |
| `GET`    | `/api/career/plans`             | List saved career plans                        |
| `GET`    | `/api/career/plans/<id>`        | One career plan                                |
| `DELETE` | `/api/career/plans/<id>`        | Delete a career plan                           |
| `POST`   | `/api/resume/analyze`           | Analyse an uploaded resume (multipart form)    |
| `GET`    | `/api/resume/analyses`          | List saved resume reports                      |
| `GET`    | `/api/resume/analyses/<id>`     | One resume report                              |
| `DELETE` | `/api/resume/analyses/<id>`     | Delete a resume report                         |

Errors always come back in the same shape, so the frontend can show a friendly message:

```json
{ "error": "Only PDF and DOCX resumes are supported. Please upload a .pdf or .docx file." }
```

---

## How data is stored

There is no database - two JSON files act as one.

`data/analyses.json`
```json
{
  "analyses": [
    {
      "id": "9f2c1ab34d5e",
      "created_at": "2026-09-30T14:30:00+00:00",
      "target_role": "Backend Developer",
      "file_name": "resume.pdf",
      "file_type": "pdf",
      "resume_chars": 4213,
      "ats_score": 72,
      "result": { "...everything Gemini returned..." }
    }
  ]
}
```

`data/career_plans.json`
```json
{
  "plans": [
    {
      "id": "b71e0c9a4f22",
      "created_at": "2026-09-30T14:35:00+00:00",
      "profile": { "education": "...", "skills": "...", "target_role": "..." },
      "result": { "...everything Gemini returned..." }
    }
  ]
}
```

Writes are **atomic** (a temp file is renamed into place) and guarded by a lock, so two
browser tabs saving at the same moment cannot corrupt the file. A damaged file is treated
as empty instead of crashing the app.

---

## Error handling

| Situation | What the user sees |
|---|---|
| No file chosen | "Please choose a resume file first." |
| A `.txt`, `.jpg`, `.zip`... | "Only PDF and DOCX resumes are supported..." |
| File over the size limit | "That file is too large (x MB). The maximum allowed size is 5 MB." |
| Scanned / image-only PDF | "We could not read enough text from that resume..." |
| Password-protected or damaged file | A specific, friendly explanation |
| Target role left empty | "Please choose or type a target job role before analyzing." |
| Wrong or expired API key | "Gemini rejected the API key. Please check GEMINI_API_KEY in your '.env' file." |
| Model not available to your key | Tells you to change `GEMINI_MODEL` in `.env` |
| Rate limited by Gemini | "Gemini is rate-limiting requests right now. Please wait a few seconds..." |
| Gemini temporarily down | "Gemini is temporarily unavailable. Please try again in a moment." |
| Content blocked by safety filters | "Gemini declined to answer this request..." |
| Anything unexpected | "Something went wrong on the server. Please try again." (with a full traceback in the terminal) |

---

## Troubleshooting

**"AI features are switched off" banner**
Your `.env` file has no key. Add `GEMINI_API_KEY=...` and restart `python app.py`.

**"The model '...' is not available for your API key"**
Open <http://127.0.0.1:5000/api/models> to see the models your key can use, then set
`GEMINI_MODEL` in `.env` to one of them and restart.

**`ModuleNotFoundError`**
Run `python -m pip install -r requirements.txt`.

**Port 5000 already in use**
Change `PORT=5001` in `.env`, or run with a different port:
`python -c "import app; app.app.run(port=5001)"`.

**PDF text comes out empty**
Your PDF is probably a scan (an image). Export a text-based PDF from Word/Google Docs,
or upload the DOCX version.

**PyPDF2 prints a DeprecationWarning**
That is the library's own notice suggesting `pypdf`. It works fine, and the app only
shows it in the terminal. Nothing to fix.

---

## Notes and limitations

- Single-user app: there is no login, so anyone who can open the URL can see the history.
  This is fine for a local student project.
- Scanned/image-only resumes cannot be read - OCR is not implemented.
- Gemini has free-tier rate limits, so very rapid repeated requests may get a "try again"
  message.
- AI output is advisory. The scores and suggestions are generated text, not verified facts.
- PyPDF2 is used for PDF text extraction; PyPDF2 is deprecated upstream in favour of
  `pypdf`, but remains fully functional here.


#   a i - c a r e e r - g u i d e - r e s u m e - a n a l y z e r  
 