/**
 * AccessRail Mobile OOP Controllers
 * - AudioVisualGuide: Spoken & visual live announcements
 * - LiveGPSMapRenderer: Clean non-overlapping schematic-GPS mobile radar
 * - AccessRailMobileApp: Orchestrates Door-to-Door Booking, Live Travel Checkpoints,
 *   Accessible Coaches, Arrival Ramp & Coach-Fullness Alerts, and Live GPS Radar.
 */

class AudioVisualGuide {
    constructor(initiallyEnabled = true) {
        this.enabled = initiallyEnabled;
        this.bannerTextEl = document.getElementById("live-guidance-text");
        this.audioLabelEl = document.getElementById("audio-state-label");
        this.updateToggleUI();
    }

    toggle() {
        this.enabled = !this.enabled;
        this.updateToggleUI();
        this.announce(
            this.enabled
                ? "Spoken audio guidance enabled."
                : "Audio muted. Visual alerts remain active.",
            true
        );
    }

    updateToggleUI() {
        if (this.audioLabelEl) {
            this.audioLabelEl.textContent = this.enabled ? "ON" : "OFF";
        }
    }

    setBanner(message) {
        if (this.bannerTextEl) {
            this.bannerTextEl.textContent = message;
        }
    }

    announce(message, forceSpeak = false) {
        this.setBanner(message);
        if ((this.enabled || forceSpeak) && "speechSynthesis" in window) {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(message);
            utterance.rate = 1.0;
            utterance.lang = "en-GB";
            window.speechSynthesis.speak(utterance);
        }
    }
}

class LiveGPSMapRenderer {
    constructor(svgElement) {
        this.svg = svgElement;
        this.corridorsLayer = document.getElementById("map-corridors-layer");
        this.stationsLayer = document.getElementById("map-stations-layer");
        this.userLayer = document.getElementById("map-user-gps-layer");
        this.trainsLayer = document.getElementById("map-trains-layer");
    }

    render(snapshot, userGps, onStationSelect) {
        if (!this.svg) return;

        const stationById = {};
        snapshot.stations.forEach((st) => {
            stationById[st.station_id] = st;
        });

        // 1. Render rail lines using well-spaced schematic coordinates
        this.corridorsLayer.innerHTML = "";
        snapshot.trains.forEach((train) => {
            const pts = train.route_station_ids
                .map((id) => stationById[id])
                .filter(Boolean)
                .map((st) => `${st.schematic_x},${st.schematic_y}`)
                .join(" ");

            const polyline = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "polyline"
            );
            polyline.setAttribute("points", pts);
            polyline.setAttribute("fill", "none");
            polyline.setAttribute("stroke", train.line_color || "#8462dc");
            polyline.setAttribute("stroke-width", "3.5");
            polyline.setAttribute("stroke-opacity", "0.4");
            polyline.setAttribute("stroke-linecap", "round");
            polyline.setAttribute("stroke-linejoin", "round");
            this.corridorsLayer.appendChild(polyline);
        });

        // 2. Render stations with clear non-overlapping labels
        this.stationsLayer.innerHTML = "";
        snapshot.stations.forEach((st) => {
            const group = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "g"
            );
            group.style.cursor = "pointer";
            group.addEventListener("click", () => onStationSelect(st.station_id));

            const isSelected = st.station_id === snapshot.selected_station_id;
            const fill = st.is_step_free_trusted ? "#34c778" : "#f09c38";

            if (isSelected) {
                const halo = document.createElementNS(
                    "http://www.w3.org/2000/svg",
                    "circle"
                );
                halo.setAttribute("cx", st.schematic_x);
                halo.setAttribute("cy", st.schematic_y);
                halo.setAttribute("r", "12");
                halo.setAttribute("fill", "rgba(52, 199, 120, 0.22)");
                halo.setAttribute("stroke", "#239459");
                halo.setAttribute("stroke-width", "1.5");
                group.appendChild(halo);
            }

            const circle = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "circle"
            );
            circle.setAttribute("cx", st.schematic_x);
            circle.setAttribute("cy", st.schematic_y);
            circle.setAttribute("r", isSelected ? "6.5" : "5.5");
            circle.setAttribute("fill", fill);
            circle.setAttribute("stroke", "#ffffff");
            circle.setAttribute("stroke-width", "2");
            group.appendChild(circle);

            const label = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "text"
            );
            const shortName = st.name.replace("Manchester ", "");
            const alignEnd = st.schematic_x > 250;
            label.setAttribute("x", st.schematic_x + (alignEnd ? -10 : 10));
            label.setAttribute("y", st.schematic_y + 4);
            if (alignEnd) {
                label.setAttribute("text-anchor", "end");
            }
            label.setAttribute("fill", isSelected ? "#2c1f4a" : "#564778");
            label.setAttribute("font-size", isSelected ? "10" : "9.2");
            label.setAttribute("font-weight", isSelected ? "800" : "600");
            label.textContent = shortName;
            group.appendChild(label);

            this.stationsLayer.appendChild(group);
        });

        // 3. Render user GPS marker near nearest station if active
        this.userLayer.innerHTML = "";
        if (userGps && snapshot.nearest_to_user) {
            const nearSt =
                stationById[snapshot.nearest_to_user.nearest_station_id];
            if (nearSt) {
                const ux = Math.max(24, nearSt.schematic_x - 24);
                const uy = Math.min(245, nearSt.schematic_y + 20);
                const pin = document.createElementNS(
                    "http://www.w3.org/2000/svg",
                    "circle"
                );
                pin.setAttribute("cx", ux);
                pin.setAttribute("cy", uy);
                pin.setAttribute("r", "6.5");
                pin.setAttribute("fill", "#239459");
                pin.setAttribute("stroke", "#ffffff");
                pin.setAttribute("stroke-width", "2");
                this.userLayer.appendChild(pin);

                const utext = document.createElementNS(
                    "http://www.w3.org/2000/svg",
                    "text"
                );
                utext.setAttribute("x", ux);
                utext.setAttribute("y", uy + 14);
                utext.setAttribute("text-anchor", "middle");
                utext.setAttribute("fill", "#135934");
                utext.setAttribute("font-size", "8.5");
                utext.setAttribute("font-weight", "800");
                utext.textContent = "YOU (GPS)";
                this.userLayer.appendChild(utext);
            }
        }

        // 4. Render moving trains with slight vertical stagger if sharing segment
        this.trainsLayer.innerHTML = "";
        snapshot.trains.forEach((train, idx) => {
            const tx = train.schematic_x;
            const ty = train.schematic_y + (idx % 2 === 0 ? -9 : 9);
            const g = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "g"
            );

            const badgeBg = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "rect"
            );
            badgeBg.setAttribute("x", tx - 21);
            badgeBg.setAttribute("y", ty - 9);
            badgeBg.setAttribute("width", "42");
            badgeBg.setAttribute("height", "18");
            badgeBg.setAttribute("rx", "6");
            badgeBg.setAttribute("fill", "#704cc9");
            badgeBg.setAttribute("stroke", "#ffffff");
            badgeBg.setAttribute("stroke-width", "1.5");
            g.appendChild(badgeBg);

            const label = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "text"
            );
            label.setAttribute("x", tx);
            label.setAttribute("y", ty + 3);
            label.setAttribute("text-anchor", "middle");
            label.setAttribute("fill", "#ffffff");
            label.setAttribute("font-size", "8.2");
            label.setAttribute("font-weight", "800");
            label.textContent = train.train_id;
            g.appendChild(label);

            this.trainsLayer.appendChild(g);
        });
    }
}

class AccessRailMobileApp {
    constructor() {
        const audioDefault = document.body.dataset.audioEnabled !== "false";
        this.isAuthenticated = document.body.dataset.authenticated === "true";
        this.defaultUserName =
            document.body.dataset.userName || "Maya Okafor (Guest)";
        this.emergencyName = document.body.dataset.emergencyName || "";
        this.emergencyPhone = document.body.dataset.emergencyPhone || "";

        this.guide = new AudioVisualGuide(audioDefault);
        this.mapRenderer = new LiveGPSMapRenderer(
            document.getElementById("manchester-gps-map")
        );

        this.stationSelect = document.getElementById("station-select");
        this.activeTrainSelect = document.getElementById("active-train-select");
        this.arrivalStationSelect = document.getElementById(
            "arrival-station-select"
        );
        this.trainsListEl = document.getElementById("trains-live-list");

        this.userGps = null;
        this.latestSnapshot = null;
        this.latestPlan = null;

        this.bindEvents();
        if (this.stationSelect) {
            this.fetchLiveTrains();
            window.setInterval(() => this.fetchLiveTrains(), 2500);
        }
    }

    bindEvents() {
        const toggleAudioBtn = document.getElementById("toggle-audio-btn");
        if (toggleAudioBtn) {
            toggleAudioBtn.addEventListener("click", () => this.guide.toggle());
        }

        const announceBtn = document.getElementById("announce-next-btn");
        if (announceBtn) {
            announceBtn.addEventListener("click", () =>
                this.announceLiveTravelUpdate()
            );
        }

        const gpsBtn = document.getElementById("locate-gps-btn");
        if (gpsBtn) {
            gpsBtn.addEventListener("click", () => this.acquireUserGPS());
        }

        if (this.stationSelect) {
            this.stationSelect.addEventListener("change", () =>
                this.fetchLiveTrains()
            );
        }

        if (this.activeTrainSelect) {
            this.activeTrainSelect.addEventListener("change", () => {
                if (this.latestSnapshot) {
                    this.renderTravelAndArrivalSections(this.latestSnapshot);
                }
            });
        }

        const planForm = document.getElementById("journey-plan-form");
        if (planForm) {
            planForm.addEventListener("submit", (e) => {
                e.preventDefault();
                this.submitJourneyPlan();
            });
        }

        const boardingRampBtn = document.getElementById(
            "notify-boarding-ramp-btn"
        );
        if (boardingRampBtn) {
            boardingRampBtn.addEventListener("click", () => {
                const trainId = this.activeTrainSelect
                    ? this.activeTrainSelect.value
                    : "TR-101";
                const originId =
                    document.getElementById("origin-station")?.value || "CHOR";
                this.sendCrewAndRampNotification(
                    trainId,
                    originId,
                    "ramp_deployment"
                );
            });
        }

        const arrivalRampBtn = document.getElementById(
            "notify-arrival-ramp-btn"
        );
        if (arrivalRampBtn) {
            arrivalRampBtn.addEventListener("click", () => {
                const trainId = this.activeTrainSelect
                    ? this.activeTrainSelect.value
                    : "TR-101";
                const destId = this.arrivalStationSelect
                    ? this.arrivalStationSelect.value
                    : "STPS";
                this.sendCrewAndRampNotification(trainId, destId, "arrival");
            });
        }

        const emergencyShareBtn = document.getElementById(
            "share-emergency-arrival-btn"
        );
        if (emergencyShareBtn) {
            emergencyShareBtn.addEventListener("click", () =>
                this.shareArrivalWithEmergencyContact()
            );
        }

        document.querySelectorAll(".report-facility-btn").forEach((btn) => {
            btn.addEventListener("click", () => {
                this.submitFacilityReport(
                    btn.dataset.station,
                    btn.dataset.status
                );
            });
        });
    }

    acquireUserGPS() {
        const readout = document.getElementById("user-gps-readout");
        const applyCoords = (lat, lon, label) => {
            this.userGps = { lat, lon };
            if (readout) {
                readout.textContent = `${label}: ${lat.toFixed(3)}°N, ${Math.abs(
                    lon
                ).toFixed(3)}°W`;
            }
            this.fetchLiveTrains(true);
        };

        if ("geolocation" in navigator) {
            navigator.geolocation.getCurrentPosition(
                (pos) =>
                    applyCoords(
                        pos.coords.latitude,
                        pos.coords.longitude,
                        "Live GPS"
                    ),
                () => applyCoords(53.4418, -2.2752, "Chorlton GPS"),
                { timeout: 3500 }
            );
        } else {
            applyCoords(53.4418, -2.2752, "Chorlton GPS");
        }
    }

    async fetchLiveTrains(announceNearest = false) {
        if (!this.stationSelect) return;
        const stationId = this.stationSelect.value;
        const params = new URLSearchParams({ station_id: stationId });
        if (this.userGps) {
            params.set("lat", String(this.userGps.lat));
            params.set("lon", String(this.userGps.lon));
        }

        try {
            const response = await fetch(`/api/trains/live?${params.toString()}`);
            if (!response.ok) return;
            const snapshot = await response.json();
            this.latestSnapshot = snapshot;

            this.mapRenderer.render(snapshot, this.userGps, (clickedStationId) => {
                this.stationSelect.value = clickedStationId;
                this.fetchLiveTrains();
            });
            this.renderStationHeader(snapshot.selected_station);
            this.renderArrivalsBoard(snapshot.trains, snapshot.selected_station);
            this.renderTravelAndArrivalSections(snapshot);

            if (announceNearest && snapshot.nearest_to_user) {
                const near = snapshot.nearest_to_user;
                this.stationSelect.value = near.recommended_step_free_station_id;
                this.guide.announce(
                    `GPS tracking active. Nearest step-free station is ${near.recommended_step_free_station_name}, ${near.recommended_distance_km} kilometres away.`
                );
            }
        } catch (err) {
            console.error("GPS feed update error:", err);
        }
    }

    renderTravelAndArrivalSections(snapshot) {
        if (!this.activeTrainSelect) return;
        const activeId = this.activeTrainSelect.value;
        const train =
            snapshot.trains.find((t) => t.train_id === activeId) ||
            snapshot.trains[0];
        if (!train) return;

        // 1. Update live intermediate spot banner & GPS coords
        const spotText = document.getElementById("travel-spot-text");
        const gpsText = document.getElementById("travel-gps-coords");
        if (spotText) {
            spotText.textContent = `${train.train_id} → ${train.headsign}: ${train.status_text}`;
        }
        if (gpsText) {
            gpsText.textContent = `📡 Live Train GPS: ${train.coordinates.latitude.toFixed(
                4
            )}°N, ${Math.abs(train.coordinates.longitude).toFixed(4)}°W · ${
                train.speed_kmh
            } km/h · Next: ${train.next_station_name} (${train.seconds_to_next_station}s)`;
        }

        this.guide.setBanner(
            `${train.train_id}: ${train.status_text} · Accessible: ${train.accessible_coaches.join(
                ", "
            )}`
        );

        // 2. Render door-to-destination checkpoint timeline
        const cpList = document.getElementById("travel-checkpoints-list");
        const postcodeVal =
            document.getElementById("origin-postcode")?.value || "M21 0UF";
        if (cpList && train.journey_checkpoints) {
            const houseStep = `<li class="cp-passed">
                <span>🏠 House Origin (${postcodeVal})</span>
                <span class="pill pill-purple">Door Commute</span>
            </li>`;
            const railSteps = train.journey_checkpoints
                .map((cp) => {
                    const cls =
                        cp.state === "current"
                            ? "cp-current"
                            : cp.state === "passed"
                            ? "cp-passed"
                            : "";
                    const badge =
                        cp.state === "current"
                            ? `<span class="pill pill-green">● Live Spot</span>`
                            : cp.state === "passed"
                            ? `<span class="pill pill-purple">✓ Passed</span>`
                            : `<span class="pill ${
                                  cp.lift_ok ? "pill-green" : "pill-amber"
                              }">${cp.lift_ok ? "Upcoming · Lift OK" : "⚠ Lift Out"}</span>`;
                    return `<li class="${cls}">
                        <span>🚉 ${cp.station_name}</span>
                        ${badge}
                    </li>`;
                })
                .join("");
            cpList.innerHTML = houseStep + railSteps;
        }

        // 3. Render Coach-by-Coach Wheelchair Accessibility & Capacity
        const coachesGrid = document.getElementById("coaches-accessibility-grid");
        if (coachesGrid && train.coaches) {
            coachesGrid.innerHTML = train.coaches
                .map((c) => {
                    const cardCls = c.is_too_full
                        ? "coach-card coach-full"
                        : c.is_wheelchair_accessible
                        ? "coach-card coach-accessible"
                        : "coach-card";
                    const badge = c.is_too_full
                        ? `<span class="pill pill-danger">⚠ TOO FULL (${c.occupancy_percent}%)</span>`
                        : c.is_wheelchair_accessible
                        ? `<span class="pill pill-green">♿ Accessible (${c.wheelchair_bays_free}/${c.wheelchair_bays_total} Free)</span>`
                        : `<span class="pill pill-purple">Standard (${c.occupancy_percent}%)</span>`;
                    return `<div class="${cardCls}">
                        <div class="coach-card-top">
                            <strong>${c.coach_id}</strong>
                            ${badge}
                        </div>
                        <div class="small-note">${c.features_label}</div>
                    </div>`;
                })
                .join("");
        }

        // 4. Update Arrival Section Coach-Too-Full Alert
        const crowdingEl = document.getElementById("arrival-crowding-alert");
        if (crowdingEl) {
            if (train.any_coach_too_full) {
                crowdingEl.className = "crowding-alert-box";
                crowdingEl.textContent = `⚠ ${train.crowding_alert}`;
            } else {
                crowdingEl.className = "crowding-alert-box crowding-clear";
                crowdingEl.textContent = `✓ ${train.crowding_alert}`;
            }
        }
    }

    renderStationHeader(station) {
        const heading = document.getElementById("selected-station-heading");
        const note = document.getElementById("selected-station-note");
        const badge = document.getElementById("selected-station-badge");
        if (heading) heading.textContent = `${station.name} Arrivals`;
        if (note) note.textContent = station.accessibility_note;
        if (badge) {
            badge.textContent = station.is_step_free_trusted
                ? "✓ Step-Free"
                : "⚠ Lift Out";
            badge.className = `pill ${
                station.is_step_free_trusted ? "pill-green" : "pill-amber"
            }`;
        }
    }

    renderArrivalsBoard(trains, selectedStation) {
        if (!this.trainsListEl) return;

        this.trainsListEl.innerHTML = trains
            .map((train) => {
                const etaDisplay = train.serves_selected_station
                    ? train.eta_selected_seconds === 0
                        ? "AT PLATFORM"
                        : `${train.eta_selected_minutes} min`
                    : `Next: ${train.eta_next_minutes}m`;

                return `
                <article class="train-item ${
                    train.has_level_boarding ? "" : "train-step-warning"
                }">
                    <div class="train-top">
                        <div>
                            <strong>${train.train_id} → ${train.headsign}</strong>
                            <div class="small-note">Accessible: ${train.accessible_coaches.join(
                                ", "
                            )}</div>
                        </div>
                        <span class="train-eta">${etaDisplay}</span>
                    </div>
                    <div class="train-meta">
                        <div>${train.status_text}</div>
                        <div class="train-gps-coord">
                            📡 ${train.coordinates.latitude.toFixed(
                                4
                            )}°N, ${Math.abs(
                    train.coordinates.longitude
                ).toFixed(4)}°W
                        </div>
                    </div>
                </article>`;
            })
            .join("");
    }

    announceLiveTravelUpdate() {
        if (!this.latestSnapshot) return;
        const activeId = this.activeTrainSelect?.value || "TR-101";
        const train =
            this.latestSnapshot.trains.find((t) => t.train_id === activeId) ||
            this.latestSnapshot.trains[0];
        if (train) {
            this.guide.announce(
                `Live update for ${train.train_id}: ${train.status_text}. Wheelchair accessible coaches are ${train.accessible_coaches.join(
                    " and "
                )}. ${train.crowding_alert}`,
                true
            );
        }
    }

    async submitJourneyPlan() {
        const originPostcode =
            document.getElementById("origin-postcode").value;
        const originAddress = document.getElementById("origin-address").value;
        const passengerCount = parseInt(
            document.getElementById("passenger-count").value || "1",
            10
        );
        const originId = document.getElementById("origin-station").value;
        const destinationId = document.getElementById(
            "destination-station"
        ).value;
        const resultBox = document.getElementById("journey-plan-result");

        const response = await fetch("/api/journey/plan", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                origin_postcode: originPostcode,
                origin_address: originAddress,
                passenger_count: passengerCount,
                origin_station_id: originId,
                destination_station_id: destinationId,
            }),
        });
        const data = await response.json();
        resultBox.classList.remove("hidden");

        if (!response.ok) {
            resultBox.innerHTML = `<div class="alert alert-error">⚠ ${data.error}</div>`;
            return;
        }

        this.latestPlan = data;
        if (this.arrivalStationSelect) {
            this.arrivalStationSelect.value = destinationId;
        }

        const commute = data.house_to_station_commute;
        const optionsHtml = data.route_options
            .map((opt, idx) => {
                const liftBadge = opt.lift_flagged
                    ? `<span class="pill pill-danger">⚠ ${opt.lift_flag_reason}</span>`
                    : `<span class="pill pill-green">✓ All Lifts &amp; Step-Free OK</span>`;
                return `
                <label class="route-option-card ${
                    opt.lift_flagged ? "route-flagged" : ""
                }">
                    <input type="radio" name="selected_route_option" value="${idx}" ${
                    idx === 0 ? "checked" : ""
                }>
                    <div style="width:100%;">
                        <div class="station-trust-title-row">
                            <strong>${opt.route_label}</strong>
                            <span class="pill pill-purple">£${opt.total_fare_gbp.toFixed(
                                2
                            )}</span>
                        </div>
                        <div class="timing-chips">
                            <span class="time-chip-house">🏠 Leave House: ${
                                opt.leave_house_time
                            }</span>
                            <span class="time-chip-train">🚆 Train ${
                                opt.train_id
                            }: ${opt.train_departure_time} → ${
                    opt.estimated_arrival_time
                }</span>
                        </div>
                        <div>${liftBadge}</div>
                        <div class="small-note">Accessible: ${opt.accessible_coaches.join(
                            ", "
                        )} · Recommended: <strong>${opt.recommended_coach}</strong></div>
                    </div>
                </label>`;
            })
            .join("");

        resultBox.innerHTML = `
            <div class="commute-walk-box">
                <strong>🏠 House-to-Station Commute (${commute.origin_postcode} → ${
            commute.station_name
        }):</strong><br>
                ${commute.route_description}
            </div>

            <div>
                <strong style="font-size:0.84rem;">Select Route Option:</strong>
                <div class="route-options-list" style="margin-top:6px;">
                    ${optionsHtml}
                </div>
            </div>

            <div class="booking-checkout-panel">
                <strong style="font-size:0.86rem;">Passenger &amp; Payment Checkout</strong>
                <div class="form-group">
                    <label for="booking-lead-name">Lead Passenger Name</label>
                    <input type="text" id="booking-lead-name" class="form-control"
                           value="${this.defaultUserName}">
                </div>
                <div class="form-group">
                    <label for="booking-companions">Other Passengers / Companions (Optional)</label>
                    <input type="text" id="booking-companions" class="form-control"
                           placeholder="e.g. Samira Patel (Companion / Colleague)">
                </div>
                <div class="form-group">
                    <label for="booking-payment-method">Payment Option</label>
                    <select id="booking-payment-method" class="form-control">
                        <option value="Apple Pay / Google Pay">Apple Pay / Google Pay (Instant)</option>
                        <option value="Saved Debit Card •••• 4821">Saved Debit Card •••• 4821</option>
                        <option value="Disabled Persons Railcard + Contactless">Disabled Persons Railcard + Contactless</option>
                        <option value="Pay at Accessible Gate">Pay at Accessible Gate</option>
                    </select>
                </div>
                <label class="preference-card-toggle" for="booking-ramp-check">
                    <input type="checkbox" id="booking-ramp-check" checked>
                    <div><strong>📐 Auto-notify train of boarding &amp; arrival ramp deployment</strong></div>
                </label>
                <button type="button" id="confirm-booking-btn" class="btn btn-green-solid full-width">
                    Confirm Booking &amp; Send Ramp Alert
                </button>
            </div>
        `;

        document
            .getElementById("confirm-booking-btn")
            .addEventListener("click", () => this.confirmRouteBooking());

        const best = data.route_options[0];
        this.guide.announce(
            `Routes found from postcode ${commute.origin_postcode}. Leave your house by ${best.leave_house_time} to catch train ${best.train_id} at ${best.train_departure_time}.`
        );
    }

    async confirmRouteBooking() {
        if (!this.latestPlan) return;
        const selectedIdx = parseInt(
            document.querySelector(
                'input[name="selected_route_option"]:checked'
            )?.value || "0",
            10
        );
        const chosen = this.latestPlan.route_options[selectedIdx];
        const passengerCount = parseInt(
            document.getElementById("passenger-count").value || "1",
            10
        );

        const response = await fetch("/api/bookings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                lead_passenger_name:
                    document.getElementById("booking-lead-name").value,
                passenger_count: passengerCount,
                companion_names:
                    document.getElementById("booking-companions").value,
                origin_postcode:
                    document.getElementById("origin-postcode").value,
                origin_address: document.getElementById("origin-address").value,
                origin_station_id: this.latestPlan.origin.station_id,
                destination_station_id: this.latestPlan.destination.station_id,
                train_id: chosen.train_id,
                selected_coach: chosen.recommended_coach,
                leave_house_time: chosen.leave_house_time,
                train_departure_time: chosen.train_departure_time,
                estimated_arrival_time: chosen.estimated_arrival_time,
                payment_method: document.getElementById(
                    "booking-payment-method"
                ).value,
                ramp_requested:
                    document.getElementById("booking-ramp-check").checked,
            }),
        });
        const resData = await response.json();
        const ticketBox = document.getElementById("booking-confirmation-box");
        ticketBox.classList.remove("hidden");

        if (!response.ok) {
            ticketBox.innerHTML = `<p>⚠ ${resData.error}</p>`;
            return;
        }

        const b = resData.booking;
        if (this.activeTrainSelect) {
            this.activeTrainSelect.value = b.train_id;
            if (this.latestSnapshot) {
                this.renderTravelAndArrivalSections(this.latestSnapshot);
            }
        }

        ticketBox.innerHTML = `
            <div class="station-trust-title-row">
                <strong>✅ E-Ticket Confirmed: ${b.booking_ref}</strong>
                <span class="pill pill-purple">Paid £${b.total_price_gbp.toFixed(
                    2
                )}</span>
            </div>
            <p style="margin:6px 0;">
                <strong>Passenger(s):</strong> ${b.lead_passenger_name} (${
            b.passenger_count
        } pax)${b.companion_names ? " + " + b.companion_names : ""}<br>
                <strong>🏠 Leave House (${b.origin_postcode}):</strong> ${
            b.leave_house_time
        }<br>
                <strong>🚆 Train ${b.train_id}:</strong> Departs ${
            b.origin_station_name
        } at ${b.train_departure_time} → Arrives ${
            b.destination_station_name
        } at ${b.estimated_arrival_time}<br>
                <strong>♿ Assigned Accessible Coach:</strong> ${
                    b.selected_coach
                } · Payment: ${b.payment_method}
            </p>
            <span class="pill pill-green">✓ Boarding &amp; Arrival Ramp Deployment Notified</span>
        `;

        this.guide.announce(
            `Booking ${b.booking_ref} confirmed! Leave house at ${b.leave_house_time} for train ${b.train_id} at ${b.train_departure_time}. Boarding and arrival ramp deployment notified.`,
            true
        );
    }

    async sendCrewAndRampNotification(trainId, stationId, stage) {
        const feedbackEl = document.getElementById("arrival-status-feedback");
        if (!this.isAuthenticated) {
            this.guide.announce(
                "Sign in as Maya Okafor or register once to send saved-profile ramp deployment notifications.",
                true
            );
            window.location.href = "/login";
            return;
        }

        const response = await fetch("/api/notify-host", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                train_id: trainId,
                station_id: stationId,
                stage: stage,
            }),
        });
        const data = await response.json();
        if (response.ok && data.notification) {
            const n = data.notification;
            const msg = `${n.status} (${n.train_id} at ${n.station_name} · Recommended: ${data.recommended_coach}). ${data.crowding_alert}`;
            if (feedbackEl) {
                feedbackEl.classList.remove("hidden");
                feedbackEl.textContent = `✓ ${msg}`;
            }
            this.guide.announce(msg, true);

            const logEl = document.getElementById("host-notifications-log");
            if (logEl) {
                const item = document.createElement("li");
                item.innerHTML = `<strong>${n.train_id} · ${n.station_name}</strong><div class="small-note">${n.message}</div><span class="pill pill-green">${n.status}</span>`;
                logEl.prepend(item);
            }
        }
    }

    shareArrivalWithEmergencyContact() {
        const feedbackEl = document.getElementById("arrival-status-feedback");
        const trainId = this.activeTrainSelect?.value || "TR-101";
        const destText =
            this.arrivalStationSelect?.options[
                this.arrivalStationSelect.selectedIndex
            ]?.text || "Destination";
        const contactLabel = this.emergencyName
            ? `${this.emergencyName} (${this.emergencyPhone})`
            : "your saved Emergency Contact";

        const text = `Live GPS location & arrival ETA on ${trainId} (${destText}) shared via SMS alert with ${contactLabel}.`;
        if (feedbackEl) {
            feedbackEl.classList.remove("hidden");
            feedbackEl.textContent = `🆘 ${text}`;
        }
        this.guide.announce(text, true);
    }

    async submitFacilityReport(stationId, status) {
        const note =
            status === "out_of_service"
                ? "LIFT OUT OF SERVICE reported live — route flagged."
                : "Lift verified back in service and step-free.";
        const response = await fetch("/api/facility/report", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                station_id: stationId,
                facility_type: "lift",
                status: status,
                note: note,
            }),
        });
        if (response.ok) {
            window.location.reload();
        }
    }
}

document.addEventListener("DOMContentLoaded", () => {
    new AccessRailMobileApp();
});
