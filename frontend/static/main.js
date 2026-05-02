

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

// Global linking status
export let isTelegramLinked = false;
export let telegramUsername = null;

export async function checkLinkStatus() {
    try {
        const response = await fetch('/api/telegram/me');
        if (response.ok) {
            const data = await response.json();
            isTelegramLinked = true;
            telegramUsername = data.username;
            document.getElementById('telegram-link-btn').innerText = `✅ Linked as ${telegramUsername}`;
            document.getElementById('telegram-link-btn').classList.add('linked');
        } else {
            isTelegramLinked = false;
            telegramUsername = null;
            document.getElementById('telegram-link-btn').innerText = '🔗 Link Telegram';
            document.getElementById('telegram-link-btn').classList.remove('linked');
        }
    } catch (error) {
        console.error('Error checking link status:', error);
    }
}

// Telegram Modal Logic
const telegramModal = document.getElementById('telegram-modal');
const telegramBtn = document.getElementById('telegram-link-btn');
const closeModal = document.querySelector('.close-modal');
const verifyBtn = document.getElementById('verify-otp-btn');
const verifyStatus = document.getElementById('verify-status');

telegramBtn.onclick = () => telegramModal.style.display = 'block';
closeModal.onclick = () => telegramModal.style.display = 'none';
window.onclick = (event) => {
    if (event.target == telegramModal) telegramModal.style.display = 'none';
}

verifyBtn.onclick = async () => {
    const username = document.getElementById('telegram-username').value;
    const otp = document.getElementById('telegram-otp').value;
    
    if (!username || !otp) {
        verifyStatus.innerText = 'Please enter both username and code.';
        verifyStatus.style.color = 'red';
        return;
    }
    
    verifyStatus.innerText = 'Verifying...';
    verifyStatus.style.color = 'blue';
    
    try {
        const response = await fetch('/api/telegram/verify_otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, otp_code: otp })
        });
        
        const data = await response.json();
        if (response.ok) {
            verifyStatus.innerText = 'Successfully linked!';
            verifyStatus.style.color = 'green';
            await checkLinkStatus();
            setTimeout(() => telegramModal.style.display = 'none', 1500);
        } else {
            verifyStatus.innerText = data.detail || 'Verification failed.';
            verifyStatus.style.color = 'red';
        }
    } catch (error) {
        verifyStatus.innerText = 'Error connecting to server.';
        verifyStatus.style.color = 'red';
    }
}

// Initial state checks and markers
checkLinkStatus();
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
