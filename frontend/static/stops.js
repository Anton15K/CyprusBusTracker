import { stopMarkersLayer, map, BusStopIcon, BusIcon, stopMarkers } from './map_logic.js'
export function updateStopMarkers() {
    const bounds = map.getBounds();
    const currentZoom = map.getZoom();
    const minZoomToShowMarkers = 16;

    let openPopupMarker = null;

    // Find the currently open popup marker, if any
    stopMarkers.forEach(marker => {
        if (marker.isPopupOpen && marker.isPopupOpen()) {
            openPopupMarker = marker;
        }
    });

    stopMarkers.forEach(marker => {
        const latLng = marker.getLatLng();
        const shouldBeVisible = currentZoom >= minZoomToShowMarkers && bounds.contains(latLng);

        if (shouldBeVisible || marker === openPopupMarker) {
            marker.addTo(stopMarkersLayer);
        } else  {
            marker.remove();
        }
    });
}
export function createStopMarkers() {
    stops.forEach(stop => {
        const latLng = [stop.stop_lat, stop.stop_lon];
        const marker = L.marker(latLng, { icon: BusStopIcon });

        // Bind the popup with a function that generates the content on the fly
        marker.bindPopup(() => {
            return `
                <div class="stop-popup">
                    <div class="stop-header">
                        <div>
                            <div class="stop-name">${stop.stop_name}</div>
                            <div class="stop-id">#${stop.stop_id}</div>
                        </div>
                        <button class="refresh-btn" onclick="window.refreshStopDetails('${stop.stop_id}')" title="Refresh">🔄</button>
                    </div>
                    <div id="route-list-${stop.stop_id}" class="route-list"><i>Fetching routes...</i></div>
                    <div id="stop-details-container-${stop.stop_id}" class="stop-details"><b>Loading upcoming arrivals...</b></div>
                </div>
            `;
        });

        // When the popup is opened, update its dynamic content
        marker.on('popupopen', () => {
            fetch(`/stops/routes_stopping_at/${stop.stop_id}`)
                .then(response => response.json())
                .then(routes => {
                    const container = document.getElementById(`route-list-${stop.stop_id}`);
                    if (container) {
                        const names = routes.map(r => r.route_short_name);
                        container.innerHTML = routes.length
                            ? `<b>Routes:</b> ${names.join(' | ')}`
                            : `<b>No route data available for this stop.</b>`;
                    }
                })
                .catch(err => {
                    console.error("Error fetching routes:", err);
                    const container = document.getElementById(`route-list-${stop.stop_id}`);
                    if (container) {
                        container.innerHTML = "Error loading routes.";
                    }
                });

            fetchStopDetails(stop.stop_id);
        });

        stopMarkers.push(marker);
    });

    updateStopMarkers(); // Maintain marker visibility
}



export function fetchStopDetails(stop_id) {
    const popupElement = document.querySelector(`#stop-details-container-${stop_id}`);
    if (!popupElement) return;

    fetch(`/stops/${stop_id}`)
        .then(response => response.json())
        .then(data => {
            if (Array.isArray(data) && data.length > 0) {
                let details = `<div class="arrival-list">`;

                data.forEach(route => {
                    details += `
                        <div class="arrival-item">
                            <span class="route-code">${route.route_short_name}</span>
                            <span class="route-desc">${route.route_long_name}</span>
                            <span class="route-time">${route.arrival_time} min</span>
                        </div>
                    `;
                });
                
                details += `</div>`;
                popupElement.innerHTML = details;
            } else {
                popupElement.innerHTML = `<b>No routes available in the next 60 minutes.</b>`;
            }
        })
        .catch(error => {
            console.error('Error fetching stop details:', error);
            popupElement.innerHTML = `<b>Failed to load stop details.</b>`;
        });
}

window.refreshStopDetails = function (stop_id) {
    const container = document.getElementById(`stop-details-container-${stop_id}`);
    if (container) {
        container.innerHTML = `<b>Refreshing...</b>`;
    }
    fetchStopDetails(stop_id);
};