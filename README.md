# AccessRail — Mobile Step-Free Transit App for Maya Okafor

A mobile-sized end-to-end Python **Flask + HTML/CSS/JS** application designed around **Maya Okafor** (32 · Policy Analyst · Manchester · Power wheelchair user) so she can travel independently, door to door, **without ringing ahead**.

## Design & UX Highlights

- **Mobile Phone Application Layout**: Styled as a native `420px` mobile phone viewport with status bar, single-column thumb-friendly cards, quick-action chips, and a sticky bottom app tab bar (**Live GPS**, **Plan Trip**, **Lifts**, **Saved Prefs / Sign In**).
- **Pastel Purple, Crisp White & Green Highlights**: Soft lavender/purple surfaces (`#faf8ff`, `#f5f0ff`, `#8b6cdf`), clean white cards (`#ffffff`), and fresh mint-green highlights (`#dcf8e6`, `#289e60`) for verified step-free access and live GPS indicators.

## Key Features

1. **One-Time User Registration & Saved Wheelchair Preferences (`/register`, `/profile`)**
   - Saves login details, home street address & postcode, mobility aid type, boarding zone, and 1-click host notification preferences permanently in SQLite.
2. **Real-Time Live GPS Train Tracking (`/`, `/api/trains/live`)**
   - Interactive Greater Manchester GPS map and live arrivals board updating train coordinates, headings, speeds, ETAs, and free wheelchair bay counts every 2.5 seconds.
3. **Spontaneous Door-to-Door Step-Free Planner & Silent Host Alerts (`/api/journey/plan`, `/api/notify-host`)**
   - Zero advance booking required; warns about broken lifts and dispatches silent digital host alerts automatically.

## Running Tests & Starting AccessRail

```bash
cd /home/devstar3754/stepfree_transit

# Run the full test suite
.venv/bin/python -m unittest discover -s tests -v

# Start the Flask server on port 5000
.venv/bin/python run.py
```
