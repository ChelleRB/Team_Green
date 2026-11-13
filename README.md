# GlidePath — Independent Step-Free Transit App for Maya Okafor

An end-to-end Python **Flask + HTML/CSS/JS** web application designed around **Maya Okafor** (32 · Policy Analyst · Manchester · Power wheelchair user) so she can travel independently, door to door, **without ringing ahead**.

## Key Features Mapped to Maya's Needs

1. **One-Time User Registration & Saved Wheelchair Preferences (`/register`, `/profile`)**
   - Stores login credentials, home street address & postcode (for door-to-door step-free origin), mobility aid type (`power` / `manual` / `scooter`), preferred accessible carriage zone, and **1-click preferences** to automatically inform train/station hosts that she is a wheelchair user.
   - Saved in SQLite so she never has to repeat her details or phone 24 hours ahead.
   - Includes a **1-Click Demo Sign-In as Maya Okafor** on the dashboard and login page.

2. **Real-Time Live GPS Train Tracking (`/`, `/api/trains/live`)**
   - Live Greater Manchester WGS84 GPS radar tracking trains across East Didsbury, Chorlton, Deansgate-Castlefield, Manchester Oxford Road, St Peter's Square, Manchester Piccadilly, and Manchester Victoria.
   - Updates live train coordinates, compass bearings, speeds, platform arrival countdowns, level-boarding verification, and free wheelchair bay counts every 2.5 seconds.
   - Supports browser live GPS geolocation (`Use My Live GPS Location`) to snap to the nearest verified step-free station.

3. **Spontaneous Door-to-Door Step-Free Planner & Silent Host Alerts (`/api/journey/plan`, `/api/notify-host`)**
   - Zero advance booking required. Automatically warns about broken lifts/ramps (e.g., Oxford Road lift fault) and dispatches silent digital host alerts using Maya's saved accessibility passport.

4. **Clear Audio & High-Contrast Visual Guidance**
   - Built-in Web Speech API spoken announcements (`Announce Next Step-Free Train`) and WCAG-inspired high-contrast dark/mint theme with large motor-friendly controls.

## Clean OOP Project Structure

```text
stepfree_transit/
├── app/                        # Main application package
│   ├── __init__.py             # Flask app factory & ServiceContainer DI
│   ├── models/                 # OOP domain entities (User, AccessibilityPreferences, Station, Train, Coordinates)
│   ├── repositories/           # Data-access layer (DatabaseManager, UserRepository, NotificationRepository)
│   ├── services/               # Business logic (AuthService, LiveGPSTrackerService, JourneyService)
│   ├── routes/                 # Web & REST API blueprints
│   ├── templates/              # Accessible Jinja2 HTML templates
│   └── static/                 # High-contrast CSS & OOP frontend JS controllers
├── tests/                      # Separate automated unit & integration test suite
│   ├── test_models.py
│   ├── test_auth_and_preferences.py
│   └── test_gps_and_api.py
├── requirements.txt
└── run.py
```

## Running Tests & Starting the App

```bash
cd /home/devstar3754/stepfree_transit

# Run the full test suite
.venv/bin/python -m unittest discover -s tests -v

# Start the Flask web server on port 5000
.venv/bin/python run.py
```

