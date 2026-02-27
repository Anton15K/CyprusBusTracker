import { busMarkers, busMarkersLayer, busMarkersMap, busPathsLayer, map, BusStopIcon, BusIcon, currentBusPath, setCurrentBusPath } from './map_logic.js'

export function updateBusMarkerVisibility() {
    var bounds = map.getBounds();
    var currentZoom = map.getZoom();
    var minZoomToShowMarkers = 11;

    Object.values(busMarkersMap).forEach(marker => {
        var latLng = marker.getLatLng();
        if (currentZoom >= minZoomToShowMarkers && bounds.contains(latLng)) {
            busMarkersLayer.addLayer(marker); // Show marker
        } else {
            busMarkersLayer.removeLayer(marker); // Hide marker
        }
    });
}

function smoothMoveMarker(marker, newLatLng, duration = 1000) {
    const startLatLng = marker.getLatLng();
    const startTime = performance.now();

    function animate(currentTime) {
        const elapsed = currentTime - startTime;
        const t = Math.min(elapsed / duration, 1); // Progress from 0 to 1

        const lat = startLatLng.lat + (newLatLng[0] - startLatLng.lat) * t;
        const lng = startLatLng.lng + (newLatLng[1] - startLatLng.lng) * t;

        marker.setLatLng([lat, lng]);

        if (t < 1) {
            requestAnimationFrame(animate);
        }
    }

    requestAnimationFrame(animate);
}

export function binarySearch(arr, target) {
    let left = 0;
    let right = arr.length - 1;
    while (left <= right) {
        const mid = (left + right) >> 1;
        if (arr[mid] === target) return true;
        if (arr[mid] < target) left = mid + 1;
        else right = mid - 1;
    }
    return false;
}

export function createOrUpdateBusMarkers(buses) {
    const seenBusIds = [];

    buses.forEach(bus => {
        const latLng = [bus.lat, bus.lon];
        const busId = bus.id;

        seenBusIds.push(busId);  // Collect existing buses for sorting later
        // console.log("Bus ID:", busId, "LatLng:", latLng);
        if (busMarkersMap[busId]) {
            // Update existing marker's position
            const iconEl = busMarkersMap[busId].getElement();
            if (iconEl) {
                const inner = iconEl.querySelector('.bus-icon-inner');
                if (inner) {
                    inner.style.transform = `rotate(${bus.bearing}deg)`;
                }
            }
            smoothMoveMarker(busMarkersMap[busId], latLng);
        } else {
            // Create new marker
            const marker = L.marker(latLng, { icon: BusIcon(bus.bearing) });

            const tooltipContent = `<b>${bus.route_short_name}</b>`;
            marker.bindTooltip(tooltipContent, { 
                permanent: true, 
                direction: 'top', 
                className: 'bus-tooltip' // custom class
            });

            marker.on('click', () => drawBusPath(bus.route_id));
            marker.on('tooltipopen', () => {
                marker.getTooltip().getElement().addEventListener('click', () => {
                    drawBusPath(bus.route_id);
                });
            });

            marker.addTo(busMarkersLayer);
            busMarkersMap[busId] = marker;
        }
    });

    // Sort the IDs to prepare for binary search
    seenBusIds.sort((a, b) => a - b);
    // console.log("Sorted seenBusIds:", seenBusIds);
    Object.keys(busMarkersMap).forEach(busId => {
        const numericBusId = Number(busId);
        if (!binarySearch(seenBusIds, numericBusId)) {
            busMarkersLayer.removeLayer(busMarkersMap[busId]);
            delete busMarkersMap[busId];
        }
    });
    // console.log("BusMarkerMap: ", busMarkersMap);
}



export function drawBusPath(route_id) {
    console.log("Before clearing, busPathsLayer has:", busPathsLayer.getLayers().length, "layers");
    busPathsLayer.clearLayers();
    setCurrentBusPath(null); // Reset the reference
    console.log("After clearing, busPathsLayer has:", busPathsLayer.getLayers().length, "layers");
    console.log("Drawing bus path for route:", route_id);
    // Fetch the bus route shape points
    fetch(`/api/get_shape/${route_id}`)
        .then(response => response.json())
        .then(shapePoints => {
            if (!shapePoints.length) {
                console.warn("No shape points returned for route:", route_id);
                return;
            }
            // Convert shape points into an array of latLng arrays
            var latLngs = shapePoints.map(point => [point.lat, point.lon]);
            // Draw the polyline for the bus route
            var polyline = L.polyline(latLngs, { color: 'green' }).addTo(busPathsLayer);
            setCurrentBusPath(polyline);
            console.log("Bus path drawn. Current bus path:", currentBusPath);
            map.fitBounds(polyline.getBounds());

            // Now fetch the bus stops along the route from the API endpoint
            // (Assuming the API expects a query parameter for the route_id)
            fetch(`/buses/get_stops_on_route/${route_id}`)
                .then(response => response.json())
                .then(stopsData => {
                    // stopsData should be an array of bus stops for the given route_id
                    stopsData.forEach(stop => {
                        // Assuming each stop has stop_lat and stop_lon properties
                        const stopLatLng = L.latLng(stop.stop_lat, stop.stop_lon);
                        // Create a circle marker to highlight the stop
                        L.circleMarker(stopLatLng, { 
                            radius: 6, 
                            color: 'green', 
                            fillColor: 'white', 
                            fillOpacity: 0.8 
                        }).addTo(busPathsLayer);
                    });
                })
                .catch(error => {
                    console.error('Error fetching stops on the route:', error);
                });
        })
        .catch(error => console.error('Error fetching shape points:', error));
}


export function refreshBuses() {
    setInterval(() => {
        fetch('/api/get_buses')
            .then(response => response.json())
            .then(data => {
                buses = data;
                createOrUpdateBusMarkers(buses); // Update locations but not visibility logic
            });
    }, 8000);
}