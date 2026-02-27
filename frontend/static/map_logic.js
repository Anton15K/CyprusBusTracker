export var map;

export var stopMarkersLayer, busMarkersLayer, busPathsLayer;
var userLocationMarker; // Start with an empty marke
export var busMarkers = []; // Store all bus markers
export var stopMarkers = []; // Store all stop markers
export var currentBusPath = null; // Reference to the current bus path
export const busMarkersMap = {}; 
export function setCurrentBusPath(path) {
    currentBusPath = path;
}



export var BusStopIcon = L.icon({
    iconUrl: '/static/images/bus-stop-icon.png', // Custom stop icon
    iconSize: [12, 12],
    iconAnchor: [6, 6],
    popupAnchor: [0, -24]
});
var userLocationIcon = L.divIcon({
    className: 'user-location-icon',
    html: `
        <div class="pulse-wrapper">
            <div class="red-ring"></div>
            <div class="pulse-ring"></div>
            <div class="pulse-center"></div>
        </div>
    `,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
});

function initMap() {
    map = L.map('map').setView([34.6786, 33.0413], 13); // Default view

    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // Initialize layers
    stopMarkersLayer = L.layerGroup().addTo(map); // Layer for bus stops
    busMarkersLayer = L.layerGroup().addTo(map);  // Layer for buses
    busPathsLayer = L.layerGroup().addTo(map);    // Layer for bus paths

    // Restore the map state once it's fully initialized
    restoreMapState();
}
function saveMapState() {
    var center = map.getCenter();
    var zoom = map.getZoom();
    localStorage.setItem("mapCenter", JSON.stringify(center));
    localStorage.setItem("mapZoom", zoom);
    console.log("Saved map state:", center, zoom);
}

// Function to restore map position from localStorage
function restoreMapState() {
    var savedCenter = localStorage.getItem("mapCenter");
    var savedZoom = localStorage.getItem("mapZoom");

    if (savedCenter && savedZoom) {
        try {
            var center = JSON.parse(savedCenter);
            var zoom = parseInt(savedZoom);
            console.log("Restoring map state:", center, zoom);
            map.setView([center.lat, center.lng], zoom);
        } catch (error) {
            console.error("Error parsing map state:", error);
        }
    }
}

function showMyLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function (position) {
            var lat = position.coords.latitude;
            var lon = position.coords.longitude;

            // Set the map view to the user's location
            map.flyTo([lat, lon], 17, {
                animate: true,
                duration: 1.5 // seconds
            });
            console.log("User's Location:", lat, lon);

            // Update the marker's position to the user's location
            if (userLocationMarker) {
                userLocationMarker.setLatLng([lat, lon])
                    // .bindPopup("You are here")
                    // .openPopup();
            } else {
                // Create a new marker with the custom icon
                userLocationMarker = L.marker([lat, lon], {
                    icon: userLocationIcon
                }).addTo(map)
                    // .bindPopup("You are here")
                    // .openPopup();
            }
        }, function (error) {
            alert("Geolocation failed: " + error.message);
        });
    } else {
        alert("Geolocation is not supported by this browser.");
    }
}
export { saveMapState, restoreMapState, initMap, showMyLocation };

export const BusIcon = (bearing) =>
    L.divIcon({
        className: "bus-icon",
        html: `<div class="bus-icon-inner" style="transform: rotate(${bearing}deg);">
                    <img src="/static/images/bus-icon.png" width="24" height="24">
               </div>`,
        iconSize: [24, 24], 
        iconAnchor: [12, 12],
    });