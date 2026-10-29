# Career Skills Assistant

An AI assistant that tells an employee what to learn next. It looks at their current skills and career goal, searches a skill list, a course catalog and internal job postings, and recommends:

- **3 skills** to build
- **2–3 courses** to take
- **1–2 roles** to grow into

Each pick comes with a one-sentence reason tied to that employee. The assistant can also enroll them in a course, but only after they say yes.

## How it works

```
You (app.py / cli.py) → Agent loop (agent.py) → AI model → Tools (tools.py) → Search (retrieval.py) → data/*.json
                                ↑                                                                      │
                                └──────────── results go back to the model until it can answer ────────┘
```

1. The employee asks a question in the browser or the terminal.
2. The agent loop sends it to the AI model along with the five tools it may use: `get_my_profile`, `search_skills`, `search_courses`, `search_jobs` and `enroll_in_course`.
3. The model picks a tool, the code runs it, and the result goes back to the model. This repeats (up to 10 steps) until the model has what it needs.
4. The final answer is checked before the employee sees it.

Search uses TF-IDF from scikit-learn (keyword matching that ranks the best results). The model is called through an OpenAI-compatible API, so any tool-calling model works. Groq is set up in `.env.example`. If the provider rate-limits a request, the agent waits and retries.

## Setup

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then fill in LLM_API_KEY and LLM_MODEL
python src/test_llm.py           # quick check that the API key and model work
```

## Run it

Run from the project root so the `data/` folder is found.

**Web demo** (opens in your browser):

```bash
streamlit run src/app.py
```

Pick an employee in the sidebar (this stands in for sign-in), then chat or click one of the example questions. Recommendations show up as cards, and "Show behind the scenes" shows which tools the AI called, whether its JSON was valid, and the time and tokens used.

**Terminal version:**

```bash
python src/cli.py --employee E001
```

There are three test employees:

| ID   | Name         | Current role             | Career goal                  |
|------|--------------|--------------------------|------------------------------|
| E001 | Maya Chen    | Data Analyst             | Move into machine learning   |
| E002 | Jordan Ellis | IT Support Specialist    | Move into cloud engineering  |
| E003 | Priya Raman  | Junior Backend Developer | Become a solutions architect |

Try asking:

- `What should I learn next?`
- `Enroll me in Intro to Machine Learning`, then `yes` (or `no`)
- `What skills does Jordan have?` (it should decline)

After each answer, both versions show which tools were called, whether the JSON was valid, and the time and tokens used.

## Keeping answers correct

AI models make mistakes, so the output is checked, not trusted:

- **Strict format.** Every reply must be one JSON object that matches a Pydantic schema (`schemas.py`). The wrong number of picks is rejected.
- **Real results only.** Every recommended course and job must have come back from an actual search, and completed courses can't be recommended (`validate.py`).
- **One retry.** If a check fails, the model is told the exact error and gets one more try. If it still fails, the employee gets a simple "please try again."
- **No endless loops.** After 10 steps the model must answer without more tool calls. Temperature is 0 for steady answers.

## Security

- **Only your own data.** The employee ID comes from sign-in (here, the `--employee` flag), never from the model, so no tool can read another person's profile.
- **Consent is decided by code.** Enrolling needs a real "yes" from the employee as their very next reply. The model can't approve it, and any other reply cancels the request.
- **Prompt injection.** Job descriptions are treated as untrusted data. Sentences that look like instructions to the AI are removed and the posting is flagged. Job `J5` in the test data contains one on purpose.
- **Allowed tools only.** Any tool name outside the five allowed ones returns an error, and bad arguments never crash the loop.
- **Secrets.** The API key lives in `.env`, which is git-ignored.

## Tests

```bash
pytest
```

The 10 tests in `tests/test_tools.py` cover profile access, search ranking, injection removal, unknown tools, bad arguments and the enrollment consent flow. They run against a temporary copy of the data and don't call the AI model.

To check the data files are consistent (every skill and course referenced actually exists):

```bash
python src/check_data.py
```

## Project layout

```
src/
  app.py          web demo (Streamlit)
  cli.py          terminal chat
  agent.py        agent loop, retries, consent check, final-answer validation
  prompts.py      system prompt
  tools.py        the five tools, scoped to one employee
  retrieval.py    TF-IDF search and prompt-injection filter
  schemas.py      Pydantic models for the reply format
  validate.py     JSON parsing and content checks
  check_data.py   data consistency check
  test_llm.py     API connection check
data/             skills, courses, jobs, employees, enrollments (JSON)
tests/            pytest tests
```

## What I'd add next

- Real company sign-in instead of a test ID
- Search by meaning (embeddings), so "ML" matches "machine learning"
- A database instead of JSON files
- A set of sample questions to score answer quality over time
- A dashboard for speed, cost and errors, built on the time and token logging that already exists
