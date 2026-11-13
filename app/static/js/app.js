/**
 * GlidePath Frontend OOP Controllers
 * - AudioVisualGuide: Web Speech API + high-contrast live status announcements
 * - LiveGPSMapRenderer: Projects WGS84 Manchester lat/lon onto interactive SVG radar
 * - GlidePathDashboardController: Polls /api/trains/live, manages 1-click host alerts & routing
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
                ? "Audio guidance enabled."
                : "Audio guidance muted. Visual guidance remains active.",
            true
        );
    }

    updateToggleUI() {
        if (this.audioLabelEl) {
            this.audioLabelEl.textContent = this.enabled ? "ON" : "MUTED";
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

        // Greater Manchester bounding box for WGS84 projection
        this.bounds = {
            minLat: 53.402,
            maxLat: 53.496,
            minLon: -2.288,
            maxLon: -2.210,
        };
        this.width = 720;
        this.height = 420;
        this.padding = 48;
    }

    project(latitude, longitude) {
        const xRatio =
            (longitude - this.bounds.minLon) /
            (this.bounds.maxLon - this.bounds.minLon);
        const yRatio =
            (latitude - this.bounds.minLat) /
            (this.bounds.maxLat - this.bounds.minLat);

        const x = this.padding + xRatio * (this.width - this.padding * 2);
        const y =
            this.height -
            (this.padding + yRatio * (this.height - this.padding * 2));
        return { x: Math.round(x * 10) / 10, y: Math.round(y * 10) / 10 };
    }

    render(snapshot, userGps, onStationSelect) {
        if (!this.svg) return;

        const stationById = {};
        snapshot.stations.forEach((st) => {
            stationById[st.station_id] = st;
        });

        // 1. Render rail corridors
        this.corridorsLayer.innerHTML = "";
        snapshot.trains.forEach((train) => {
            const pts = train.route_station_ids
                .map((id) => stationById[id])
                .filter(Boolean)
                .map((st) => {
                    const p = this.project(
                        st.coordinates.latitude,
                        st.coordinates.longitude
                    );
                    return `${p.x},${p.y}`;
                })
                .join(" ");

            const polyline = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "polyline"
            );
            polyline.setAttribute("points", pts);
            polyline.setAttribute("fill", "none");
            polyline.setAttribute("stroke", train.line_color || "#80ef80");
            polyline.setAttribute("stroke-width", "4");
            polyline.setAttribute("stroke-opacity", "0.35");
            polyline.setAttribute("stroke-linecap", "round");
            polyline.setAttribute("stroke-linejoin", "round");
            this.corridorsLayer.appendChild(polyline);
        });

        // 2. Render stations
        this.stationsLayer.innerHTML = "";
        snapshot.stations.forEach((st) => {
            const pos = this.project(
                st.coordinates.latitude,
                st.coordinates.longitude
            );
            const group = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "g"
            );
            group.style.cursor = "pointer";
            group.addEventListener("click", () => onStationSelect(st.station_id));

            const isSelected = st.station_id === snapshot.selected_station_id;
            const fill = st.is_step_free_trusted ? "#80ef80" : "#ffb347";

            if (isSelected) {
                const halo = document.createElementNS(
                    "http://www.w3.org/2000/svg",
                    "circle"
                );
                halo.setAttribute("cx", pos.x);
                halo.setAttribute("cy", pos.y);
                halo.setAttribute("r", "15");
                halo.setAttribute("fill", "rgba(128, 239, 128, 0.22)");
                halo.setAttribute("stroke", "#80ef80");
                halo.setAttribute("stroke-width", "1.5");
                group.appendChild(halo);
            }

            const circle = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "circle"
            );
            circle.setAttribute("cx", pos.x);
            circle.setAttribute("cy", pos.y);
            circle.setAttribute("r", isSelected ? "8" : "6.5");
            circle.setAttribute("fill", fill);
            circle.setAttribute("stroke", "#141815");
            circle.setAttribute("stroke-width", "2");
            group.appendChild(circle);

            const label = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "text"
            );
            const offsetX = st.station_id === "OXFD" ? -12 : 12;
            const offsetY = st.station_id === "STPS" ? -10 : 5;
            label.setAttribute("x", pos.x + offsetX);
            label.setAttribute("y", pos.y + offsetY);
            if (st.station_id === "OXFD") {
                label.setAttribute("text-anchor", "end");
            }
            label.setAttribute("fill", isSelected ? "#ffffff" : "#d5dad2");
            label.setAttribute("font-size", isSelected ? "13" : "11.5");
            label.setAttribute("font-weight", isSelected ? "800" : "600");
            label.textContent = st.name;
            group.appendChild(label);

            this.stationsLayer.appendChild(group);
        });

        // 3. Render user's live GPS pin if active
        this.userLayer.innerHTML = "";
        if (userGps) {
            const upos = this.project(userGps.lat, userGps.lon);
            const pin = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "circle"
            );
            pin.setAttribute("cx", upos.x);
            pin.setAttribute("cy", upos.y);
            pin.setAttribute("r", "9");
            pin.setAttribute("fill", "#ffffff");
            pin.setAttribute("stroke", "#80ef80");
            pin.setAttribute("stroke-width", "3");
            this.userLayer.appendChild(pin);

            const utext = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "text"
            );
            utext.setAttribute("x", upos.x);
            utext.setAttribute("y", upos.y - 14);
            utext.setAttribute("text-anchor", "middle");
            utext.setAttribute("fill", "#80ef80");
            utext.setAttribute("font-size", "11");
            utext.setAttribute("font-weight", "800");
            utext.textContent = "YOU (GPS)";
            this.userLayer.appendChild(utext);
        }

        // 4. Render live moving GPS trains
        this.trainsLayer.innerHTML = "";
        snapshot.trains.forEach((train) => {
            const tpos = this.project(
                train.coordinates.latitude,
                train.coordinates.longitude
            );
            const g = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "g"
            );

            const badgeBg = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "rect"
            );
            badgeBg.setAttribute("x", tpos.x - 28);
            badgeBg.setAttribute("y", tpos.y - 12);
            badgeBg.setAttribute("width", "56");
            badgeBg.setAttribute("height", "24");
            badgeBg.setAttribute("rx", "7");
            badgeBg.setAttribute("fill", "#1a242b");
            badgeBg.setAttribute("stroke", train.line_color || "#56c8ff");
            badgeBg.setAttribute("stroke-width", "2");
            g.appendChild(badgeBg);

            const label = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "text"
            );
            label.setAttribute("x", tpos.x);
            label.setAttribute("y", tpos.y + 4);
            label.setAttribute("text-anchor", "middle");
            label.setAttribute("fill", "#ffffff");
            label.setAttribute("font-size", "10.5");
            label.setAttribute("font-weight", "800");
            label.textContent = train.train_id;
            g.appendChild(label);

            this.trainsLayer.appendChild(g);
        });
    }
}

class GlidePathDashboardController {
    constructor() {
        const audioDefault =
            document.body.dataset.audioEnabled !== "false";
        this.isAuthenticated =
            document.body.dataset.authenticated === "true";
        this.guide = new AudioVisualGuide(audioDefault);
        this.mapRenderer = new LiveGPSMapRenderer(
            document.getElementById("manchester-gps-map")
        );

        this.stationSelect = document.getElementById("station-select");
        this.trainsListEl = document.getElementById("trains-live-list");
        this.userGps = null;
        this.latestSnapshot = null;
        this.pollTimer = null;

        this.bindEvents();
        if (this.stationSelect) {
            this.fetchLiveTrains();
            this.pollTimer = window.setInterval(
                () => this.fetchLiveTrains(),
                2500
            );
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
                this.announceNextStepFreeTrain()
            );
        }

        const gpsBtn = document.getElementById("locate-gps-btn");
        if (gpsBtn) {
            gpsBtn.addEventListener("click", () => this.acquireUserGPS());
        }

        if (this.stationSelect) {
            this.stationSelect.addEventListener("change", () => {
                this.fetchLiveTrains();
            });
        }

        const planForm = document.getElementById("journey-plan-form");
        if (planForm) {
            planForm.addEventListener("submit", (e) => {
                e.preventDefault();
                this.submitJourneyPlan();
            });
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
                readout.textContent = `${label}: ${lat.toFixed(4)}°N, ${Math.abs(lon).toFixed(4)}°W`;
            }
            this.fetchLiveTrains(true);
        };

        if ("geolocation" in navigator) {
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    applyCoords(
                        pos.coords.latitude,
                        pos.coords.longitude,
                        "Live GPS"
                    );
                },
                () => {
                    // Fallback to Maya's Chorlton Manchester GPS coordinates in restricted sandboxes
                    applyCoords(53.4418, -2.2752, "Manchester Home GPS");
                },
                { timeout: 3500 }
            );
        } else {
            applyCoords(53.4418, -2.2752, "Manchester Home GPS");
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

            const nextServing = snapshot.trains.find(
                (t) => t.serves_selected_station
            );
            if (nextServing) {
                const etaLabel =
                    nextServing.eta_selected_seconds === 0
                        ? "at platform now"
                        : `in ${nextServing.eta_selected_minutes} min (${nextServing.eta_selected_seconds}s)`;
                this.guide.setBanner(
                    `Live GPS: ${nextServing.train_id} to ${nextServing.headsign} arriving at ${snapshot.selected_station.name} ${etaLabel} · ${nextServing.accessible_carriage}.`
                );
            }

            if (announceNearest && snapshot.nearest_to_user) {
                const near = snapshot.nearest_to_user;
                this.stationSelect.value = near.recommended_step_free_station_id;
                this.guide.announce(
                    `GPS locked. Nearest verified step-free station is ${near.recommended_step_free_station_name}, ${near.recommended_distance_km} kilometres away.`
                );
            }
        } catch (err) {
            console.error("GPS feed update error:", err);
        }
    }

    renderStationHeader(station) {
        const heading = document.getElementById("selected-station-heading");
        const note = document.getElementById("selected-station-note");
        const badge = document.getElementById("selected-station-badge");
        if (heading) heading.textContent = `${station.name} — Live Arrivals`;
        if (note) note.textContent = station.accessibility_note;
        if (badge) {
            badge.textContent = station.trust_badge;
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
                        : `${train.eta_selected_minutes} min (${train.eta_selected_seconds}s)`
                    : `Next stop: ${train.eta_next_minutes} min`;

                const stepBadge = train.has_level_boarding
                    ? `<span class="pill pill-green">✓ Step-Free Level Boarding</span>`
                    : `<span class="pill pill-amber">⚠ Auto-Ramp via Host</span>`;

                return `
                <article class="train-item ${
                    train.has_level_boarding ? "" : "train-step-warning"
                }">
                    <div class="train-top">
                        <div>
                            <strong>${train.train_id} → ${train.headsign}</strong>
                            <div><small class="muted">${train.line_name}</small></div>
                        </div>
                        <span class="train-eta">${etaDisplay}</span>
                    </div>
                    <div class="train-meta">
                        <div>${stepBadge} <span class="pill pill-dark">♿ ${
                    train.wheelchair_bays_free
                }/${train.wheelchair_bays_total} Bays Free</span></div>
                        <div><strong>Zone:</strong> ${train.accessible_carriage}</div>
                        <div><strong>Status:</strong> ${train.status_text}</div>
                        <div class="train-gps-coord">
                            📡 GPS: ${train.coordinates.latitude.toFixed(5)}°N, ${Math.abs(
                    train.coordinates.longitude
                ).toFixed(5)}°W · Heading ${train.heading_deg}° · ${train.speed_kmh} km/h
                        </div>
                    </div>
                    <div class="train-actions">
                        <button type="button" class="btn btn-primary btn-xs notify-host-btn"
                                data-train="${train.train_id}"
                                data-station="${selectedStation.station_id}">
                            ♿ Board &amp; Silent-Ping Host
                        </button>
                    </div>
                </article>`;
            })
            .join("");

        this.trainsListEl
            .querySelectorAll(".notify-host-btn")
            .forEach((btn) => {
                btn.addEventListener("click", () =>
                    this.sendOneClickHostPing(
                        btn.dataset.train,
                        btn.dataset.station
                    )
                );
            });
    }

    announceNextStepFreeTrain() {
        if (!this.latestSnapshot) return;
        const station = this.latestSnapshot.selected_station;
        const candidate = this.latestSnapshot.trains.find(
            (t) => t.serves_selected_station && t.has_level_boarding
        );
        if (candidate) {
            const etaText =
                candidate.eta_selected_seconds === 0
                    ? "is boarding right now"
                    : `arrives in ${candidate.eta_selected_minutes} minutes`;
            this.guide.announce(
                `Next step-free train at ${station.name}: ${candidate.train_id} towards ${candidate.headsign} ${etaText}. Proceed to ${candidate.accessible_carriage}. ${candidate.wheelchair_bays_free} wheelchair bays are free.`,
                true
            );
        } else {
            this.guide.announce(
                `No direct level-boarding train currently scheduled at ${station.name}. Check Deansgate or Piccadilly.`,
                true
            );
        }
    }

    async sendOneClickHostPing(trainId, stationId) {
        if (!this.isAuthenticated) {
            this.guide.announce(
                "Sign in as Maya Okafor or register once to save your wheelchair preferences for one-click host alerts.",
                true
            );
            window.location.href = "/login";
            return;
        }

        try {
            const response = await fetch("/api/notify-host", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ train_id: trainId, station_id: stationId }),
            });
            const data = await response.json();
            if (response.ok && data.notification) {
                const n = data.notification;
                this.guide.announce(
                    `Host notified silently for train ${n.train_id} at ${n.station_name}. Your saved ${n.wheelchair_type} wheelchair preference and ${n.preferred_carriage} were sent automatically.`,
                    true
                );
                const logEl = document.getElementById("host-notifications-log");
                if (logEl) {
                    const item = document.createElement("li");
                    item.innerHTML = `<strong>${n.train_id} at ${n.station_name}</strong> — <span>${n.preferred_carriage}</span> <span class="pill pill-green">${n.status}</span>`;
                    logEl.prepend(item);
                }
            }
        } catch (err) {
            console.error("Failed to notify host:", err);
        }
    }

    async submitJourneyPlan() {
        const originId = document.getElementById("origin-station").value;
        const destinationId = document.getElementById("destination-station").value;
        const resultBox = document.getElementById("journey-plan-result");

        const response = await fetch("/api/journey/plan", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                origin_station_id: originId,
                destination_station_id: destinationId,
            }),
        });
        const data = await response.json();
        resultBox.classList.remove("hidden");

        if (!response.ok) {
            resultBox.innerHTML = `<p><strong>⚠ ${data.error}</strong></p>`;
            return;
        }

        const warningsHtml =
            data.warnings && data.warnings.length
                ? `<div class="alert alert-error">${data.warnings.join("<br>")}</div>`
                : `<div class="pill pill-green">✓ 100% Verified Step-Free Door-to-Door Route</div>`;

        const stepsHtml = data.steps
            .map(
                (s) =>
                    `<li><strong>${s.title}:</strong> ${s.detail}</li>`
            )
            .join("");

        const hostBanner = data.auto_host_notification
            ? `<p class="small-note">📡 <strong>Auto-Host Alert Sent:</strong> ${data.auto_host_notification.status} (${data.auto_host_notification.preferred_carriage})</p>`
            : "";

        resultBox.innerHTML = `
            ${warningsHtml}
            <ol class="journey-steps">${stepsHtml}</ol>
            ${hostBanner}
        `;

        this.guide.announce(
            `Step-free route ready from ${data.origin.name} to ${data.destination.name}. Board ${data.recommended_train.train_id}.`
        );
    }

    async submitFacilityReport(stationId, status) {
        const note =
            status === "out_of_service"
                ? "ALERT: Lift reported out of service by commuter — route via step-free alternative."
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
    new GlidePathDashboardController();
});

