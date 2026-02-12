let phase = 0; // 0 = idle, 1 = picking destination, 2 = picking origin
let destination = null;
let origin = null;

let destMarker = null;
let originMarker = null;

// Global array to store current route layers on the map
let currentRouteLayers = [];

// Reference to the cancel (cross) button. Ensure it exists in your HTML.
const cancelRouteBtn = document.getElementById("cancelRouteBtn");

export function initRouteMaking(map, makeRouteBtn, doneBtn, backBtn) {
    const label = document.getElementById("route-label");
    const centerMarker = document.getElementById("center-marker");

    const destIcon = L.icon({
        iconUrl: '/static/images/pin-icon.png',
        iconSize: [30, 30],
        iconAnchor: [15, 30],
    });

    const originIcon = L.icon({
        iconUrl: '/static/images/pin-icon.png',
        iconSize: [30, 30],
        iconAnchor: [15, 30],
    });

    // Resets all markers, route layers, and summary bars. Also hides the cancel button.
    function reset() {
        label.innerText = "";
        destination = null;
        origin = null;
        phase = 0;
    
        if (destMarker) {
            map.removeLayer(destMarker);
            destMarker = null;
        }
        if (originMarker) {
            map.removeLayer(originMarker);
            originMarker = null;
        }
    
        const summaryContainer = document.getElementById("routeSummaries");
        summaryContainer.innerHTML = "";
        summaryContainer.style.display = "none";
    
        if (currentRouteLayers.length > 0) {
            currentRouteLayers.forEach(layer => map.removeLayer(layer));
            currentRouteLayers = [];
        }
    
        centerMarker.style.display = "none";
        cancelRouteBtn.style.display = "none";
    }
    
    // toggleUI hides/shows the routeButtons and label.
    // The cancel button is not controlled here because it appears only after "Done".
    function toggleUI(active) {
        makeRouteBtn.style.display = active ? "none" : "inline-block";
        document.getElementById("routeButtons").style.display = active ? "flex" : "none";
        label.style.display = active ? "block" : "none";
    }
    
    // When "Make Route" is pressed, we clear any existing routes/markers and hide the cancel button.
    makeRouteBtn.addEventListener('click', () => {
        reset();
        phase = 1;
        label.innerText = "Where to?";
        toggleUI(true);
        centerMarker.style.display = "block";
    });
    
    // The cancel button appears only after routes have been created.
    // When pressed, it resets the UI.
    cancelRouteBtn.addEventListener('click', () => {
        reset();
    });
    
    doneBtn.addEventListener('click', () => {
        const center = map.getCenter();
    
        if (phase === 1) {
            destination = center;
            destMarker = L.marker(center, { icon: destIcon }).addTo(map);
            label.innerText = "Where from?";
            phase = 2;
        } else if (phase === 2) {
            origin = center;
            originMarker = L.marker(center, { icon: originIcon }).addTo(map);
    
            label.innerText = "";
            centerMarker.style.display = "none";
            toggleUI(false);
            phase = 0;
    
            console.log("Route from", origin, "to", destination);
    
            // Send POST request to /api/make_route and expect an array of routes
            fetch('/api/make_route', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    origin: { lat: origin.lat, lng: origin.lng },
                    destination: { lat: destination.lat, lng: destination.lng }
                })
            })
            .then(response => response.json())
            .then(routes => {
                if (!Array.isArray(routes) || routes.length === 0) {
                    alert("No route returned from server.");
                    return;
                }
                
                // Create or clear the summary container and set it visible
                const summaryContainer = document.getElementById("routeSummaries");
                summaryContainer.innerHTML = "";
                summaryContainer.style.display = "flex";
                
                // Clear global route layers array
                currentRouteLayers = [];
    
                // Process top 3 routes (assumed in the response as edges with node objects)
                routes.slice(0, 3).forEach((edge, index) => {
                    const node = edge.node;
                    if (!node.legs || !Array.isArray(node.legs)) {
                        console.error("No legs for this route:", edge);
                        return;
                    }
                    
                    // Create a LayerGroup for this route
                    const routeLayer = L.layerGroup();
    
                    // For each leg, add its polyline to the layer group
                    node.legs.forEach(leg => {
                        const latLngs = leg.legGeometry.points.map(point => [point[0], point[1]]);
                        const color = leg.mode === "WALK" ? "blue" : "green";
                        const dashArray = leg.mode === "WALK" ? "5, 10" : null;
    
                        const polyline = L.polyline(latLngs, {
                            color: color,
                            dashArray: dashArray,
                            weight: 4,
                            opacity: 0.9
                        });
                        polyline.addTo(routeLayer);
                    });
                    
                    // Save the layer for switching between routes
                    currentRouteLayers.push(routeLayer);
    
                    // Create a summary bar for this route.
                    const bar = document.createElement("div");
                    bar.classList.add("route-summary-bar");
    
                    // Extract times (assuming ISO strings) and compute duration in minutes.
                    const startTimeStr = node.start ? node.start.slice(11, 16) : "??:??";
                    const endTimeStr = node.end ? node.end.slice(11, 16) : "??:??";
                    let durationMins = 0;
                    if (node.start && node.end) {
                        const startDate = new Date(node.start);
                        const endDate = new Date(node.end);
                        durationMins = Math.round((endDate - startDate) / 60000);
                    }
    
                    // Build a leg summary with separate durations
                    const legSummary = node.legs.map(leg => {
                        const legStart = leg.from.arrival?.scheduledTime || leg.from.departure?.scheduledTime || node.start;
                        const legEnd = leg.to.arrival?.scheduledTime || leg.to.departure?.scheduledTime || node.end;
                        let legDurMin = 0;
                        if (legStart && legEnd) {
                            const lStart = new Date(legStart);
                            const lEnd = new Date(legEnd);
                            legDurMin = Math.round((lEnd - lStart) / 60000);
                        }
                        if (leg.mode === "WALK") return `<span class="walk">Walk: ${legDurMin} min</span>`;
                        if (leg.mode === "BUS") {
                            const busNumber = leg.route && leg.route.shortName ? leg.route.shortName : "Bus";
                            return `<span class="bus-leg"><span class="bus-number">${busNumber}</span> ${legDurMin} min</span>`;
                        }
                        return `<span>${leg.mode}: ${legDurMin} min</span>`;
                    }).join(" → ");
    
                    bar.innerHTML = `
                        <div class="route-time">
                            <span class="start-time">${startTimeStr}</span> - 
                            <span class="end-time">${endTimeStr}</span> 
                            <span class="total-duration">(${durationMins} min)</span>
                        </div>
                        <div class="route-leg-summary">${legSummary}</div>
                    `;
    
                    // When the bar is clicked, show only this route on the map.
                    bar.addEventListener("click", () => {
                        currentRouteLayers.forEach(layer => map.removeLayer(layer));
                        routeLayer.addTo(map);
                        document.querySelectorAll(".route-summary-bar").forEach(el => el.classList.remove("highlight"));
                        bar.classList.add("highlight");
                        // map.fitBounds(routeLayer.getBounds());
                    });
    
                    summaryContainer.appendChild(bar);
                });
                
                // Automatically highlight and show the fastest (first) route
                if (currentRouteLayers.length > 0) {
                    currentRouteLayers[0].addTo(map);
                    const firstBar = summaryContainer.querySelector(".route-summary-bar");
                    if (firstBar) firstBar.classList.add("highlight");
                    // map.fitBounds(currentRouteLayers[0].getBounds());
                }
    
                // Now that routes are shown, display the cancel button.
                cancelRouteBtn.style.display = "inline-block";
            })
            .catch(err => {
                console.error("Failed to fetch route:", err);
                alert("Failed to fetch route from server.");
            });
        }
    });
    
    backBtn.addEventListener('click', () => {
        if (phase === 2) {
            if (destMarker) {
                map.removeLayer(destMarker);
                destMarker = null;
            }
            destination = null;
            phase = 1;
            label.innerText = "Where to?";
        } else if (phase === 1) {
            reset();
            toggleUI(false);
        }
    });
}
