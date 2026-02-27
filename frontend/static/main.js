

import { map, busPathsLayer, currentBusPath, setCurrentBusPath, restoreMapState, saveMapState, initMap, showMyLocation } from './map_logic.js'; // Import map and layers

import { updateStopMarkers, createStopMarkers, fetchStopDetails } from './stops.js';
import { createOrUpdateBusMarkers, updateBusMarkerVisibility, refreshBuses } from './buses.js';
import { initRouteMaking } from './route_making.js';

// Call initMap when the page loads
initMap();
map.on('click', function() {
    if (currentBusPath) {
        busPathsLayer.clearLayers();  // Remove the current bus path
        setCurrentBusPath(null); // Reset the reference
        console.log("Bus path removed on map click");
    }
});

const makeRouteBtn = document.getElementById('makeRouteBtn');
const doneBtn = document.getElementById('doneBtn');
const backBtn = document.getElementById('backBtn');

// Initialize route making functionality
initRouteMaking(map, makeRouteBtn, doneBtn, backBtn);
document.getElementById('show-location-btn').addEventListener('click', function() {
  showMyLocation();
});

// Initial marker updates
createStopMarkers();  
fetch('/api/get_buses')
  .then(response => response.json())
  .then(data => {
      buses = data;
      createOrUpdateBusMarkers(buses); // Update locations but not visibility logic
});
updateBusMarkerVisibility();

// Attach zoom & move event listeners
map.on('moveend', updateBusMarkerVisibility);
map.on('zoomend', updateBusMarkerVisibility);

window.addEventListener('beforeunload', saveMapState);

// Update markers when the map is moved or zoomed
map.on('moveend', updateStopMarkers);
map.on('zoomend', updateStopMarkers);

// Refreshes buses every 8 seconds
refreshBuses();
