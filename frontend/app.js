/**
 * Smart Home Dashboard — Frontend JavaScript
 * =============================================
 *
 * WHAT: Manages the device UI, WebSocket real-time updates, and API interactions.
 * WHY:  Provides a live, interactive dashboard for monitoring and controlling devices.
 * HOW:  Fetches devices on load, renders cards, listens for WebSocket broadcasts,
 *       and updates the DOM in real-time without page reloads.
 *
 * No build tools, no frameworks — just clean vanilla JavaScript.
 */

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

const API_BASE = window.location.origin + '/api';
const WS_URL = `ws://${window.location.host}/ws`;

// Device type → emoji icon mapping
const DEVICE_ICONS = {
    light:      '💡',
    fan:        '🌀',
    thermostat: '🌡️',
    lock:       '🔒',
    camera:     '📷',
    speaker:    '🔊',
    blinds:     '🪟',
    outlet:     '🔌',
    default:    '📦'
};

// ═══════════════════════════════════════════════════════════════════════════════
// STATE — Single source of truth for the frontend
// ═══════════════════════════════════════════════════════════════════════════════

let devices = [];
let activeFilter = 'all';
let ws = null;
let wsReconnectTimer = null;

// ═══════════════════════════════════════════════════════════════════════════════
// DOM REFERENCES
// ═══════════════════════════════════════════════════════════════════════════════

const $grid         = document.getElementById('device-grid');
const $loading      = document.getElementById('loading-state');
const $empty        = document.getElementById('empty-state');
const $statTotal    = document.getElementById('stat-total');
const $statOn       = document.getElementById('stat-on');
const $statOff      = document.getElementById('stat-off');
const $statRooms    = document.getElementById('stat-rooms');
const $filterBar    = document.getElementById('filter-bar');
const $connStatus   = document.getElementById('connection-status');
const $connText     = $connStatus.querySelector('.status-text');
const $logPanel     = document.getElementById('log-panel');
const $logList      = document.getElementById('log-list');
const $toastContainer = document.getElementById('toast-container');

// ═══════════════════════════════════════════════════════════════════════════════
// API CALLS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Fetch all devices from the backend.
 */
async function fetchDevices() {
    try {
        const res = await fetch(`${API_BASE}/devices`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        devices = await res.json();
        return devices;
    } catch (err) {
        console.error('Failed to fetch devices:', err);
        showToast('❌', 'Failed to load devices. Is the backend running?');
        return [];
    }
}

/**
 * Toggle a device's state via the API.
 */
async function toggleDevice(deviceId) {
    try {
        const res = await fetch(`${API_BASE}/devices/${deviceId}/toggle`, { method: 'POST' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (err) {
        console.error('Failed to toggle device:', err);
        showToast('❌', 'Failed to toggle device');
        return null;
    }
}

/**
 * Update a device's brightness.
 */
async function updateBrightness(deviceId, brightness) {
    try {
        const res = await fetch(`${API_BASE}/devices/${deviceId}/brightness`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ brightness, source: 'frontend' })
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (err) {
        console.error('Failed to update brightness:', err);
        showToast('❌', 'Failed to update brightness');
        return null;
    }
}

/**
 * Fetch action logs from the backend.
 */
async function fetchLogs() {
    try {
        const res = await fetch(`${API_BASE}/logs?limit=30`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (err) {
        console.error('Failed to fetch logs:', err);
        return [];
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// RENDERING
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Render the device grid based on current state and active filter.
 */
function renderDevices() {
    // Filter devices by room if a filter is active
    const filtered = activeFilter === 'all'
        ? devices
        : devices.filter(d => d.room === activeFilter);

    // Show/hide empty state
    $loading.classList.add('hidden');
    $empty.classList.toggle('hidden', filtered.length > 0);

    // Build HTML for all device cards
    $grid.innerHTML = filtered.map(device => createDeviceCard(device)).join('');

    // Attach event listeners to the new cards
    attachCardListeners();

    // Update stats
    updateStats();

    // Update room filters
    updateFilters();
}

/**
 * Create HTML for a single device card.
 */
function createDeviceCard(device) {
    const isOn = device.state === 'on';
    const icon = DEVICE_ICONS[device.type] || DEVICE_ICONS.default;

    return `
        <div class="device-card ${isOn ? 'is-on' : ''}" data-device-id="${device.id}" id="device-card-${device.id}">
            <div class="card-top">
                <div class="device-icon-wrapper">${icon}</div>
                <label class="toggle-switch" title="Toggle ${device.name}">
                    <input type="checkbox" ${isOn ? 'checked' : ''} data-toggle-id="${device.id}" id="toggle-${device.id}">
                    <span class="toggle-slider"></span>
                </label>
            </div>
            <div class="device-name">
                ${device.name}
                <span class="device-type-badge">${device.type}</span>
            </div>
            <div class="device-room">📍 ${device.room}</div>
            <div class="device-status ${isOn ? 'status-on' : 'status-off'}">
                <span>${isOn ? '● Active' : '○ Inactive'}</span>
            </div>
            <div class="brightness-control">
                <div class="brightness-label">
                    <span>Brightness</span>
                    <span class="brightness-value" id="brightness-val-${device.id}">${device.brightness}%</span>
                </div>
                <input type="range" class="brightness-slider" min="0" max="100" 
                       value="${device.brightness}" data-brightness-id="${device.id}" 
                       id="brightness-slider-${device.id}">
            </div>
        </div>
    `;
}

/**
 * Attach toggle and brightness event listeners to device cards.
 */
function attachCardListeners() {
    // Toggle switches
    document.querySelectorAll('[data-toggle-id]').forEach(toggle => {
        toggle.addEventListener('change', async (e) => {
            const deviceId = parseInt(e.target.dataset.toggleId);
            const result = await toggleDevice(deviceId);
            if (result) {
                // Update local state
                const idx = devices.findIndex(d => d.id === deviceId);
                if (idx !== -1) devices[idx] = result;
                // Note: WebSocket will handle the re-render for real-time sync
            }
        });
    });

    // Brightness sliders — debounced to avoid flooding the API
    document.querySelectorAll('[data-brightness-id]').forEach(slider => {
        let debounceTimer;
        const deviceId = parseInt(slider.dataset.brightnessId);

        // Update label immediately on input
        slider.addEventListener('input', (e) => {
            const label = document.getElementById(`brightness-val-${deviceId}`);
            if (label) label.textContent = `${e.target.value}%`;
        });

        // Send API call on change (after user releases the slider)
        slider.addEventListener('change', async (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(async () => {
                const brightness = parseInt(e.target.value);
                const result = await updateBrightness(deviceId, brightness);
                if (result) {
                    const idx = devices.findIndex(d => d.id === deviceId);
                    if (idx !== -1) devices[idx] = result;
                }
            }, 200);
        });
    });
}

/**
 * Update the stats bar with current device counts.
 */
function updateStats() {
    const total = devices.length;
    const on = devices.filter(d => d.state === 'on').length;
    const off = total - on;
    const rooms = new Set(devices.map(d => d.room)).size;

    animateCounter($statTotal, total);
    animateCounter($statOn, on);
    animateCounter($statOff, off);
    animateCounter($statRooms, rooms);
}

/**
 * Smoothly animate a counter from its current value to the target.
 */
function animateCounter(el, target) {
    const current = parseInt(el.textContent) || 0;
    if (current === target) return;

    const duration = 400;
    const steps = 20;
    const increment = (target - current) / steps;
    let step = 0;

    const timer = setInterval(() => {
        step++;
        if (step >= steps) {
            el.textContent = target;
            clearInterval(timer);
        } else {
            el.textContent = Math.round(current + increment * step);
        }
    }, duration / steps);
}

/**
 * Update room filter chips based on available devices.
 */
function updateFilters() {
    const rooms = [...new Set(devices.map(d => d.room))].sort();

    // Keep "All Rooms" + add room chips
    $filterBar.innerHTML = `
        <button class="filter-chip ${activeFilter === 'all' ? 'active' : ''}" 
                data-room="all" id="filter-all">All Rooms</button>
        ${rooms.map(room => `
            <button class="filter-chip ${activeFilter === room ? 'active' : ''}" 
                    data-room="${room}" id="filter-${room.replace(/\s+/g, '-').toLowerCase()}">${room}</button>
        `).join('')}
    `;

    // Attach filter click listeners
    $filterBar.querySelectorAll('.filter-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            activeFilter = chip.dataset.room;
            renderDevices();
        });
    });
}

// ═══════════════════════════════════════════════════════════════════════════════
// WEBSOCKET — Real-time updates
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Connect to the WebSocket server for real-time device updates.
 *
 * IMPORTANT: Includes auto-reconnect logic. If the server restarts,
 * the frontend will automatically reconnect after 3 seconds.
 */
function connectWebSocket() {
    // Clean up any existing connection
    if (ws) {
        ws.close();
    }

    try {
        ws = new WebSocket(WS_URL);

        ws.onopen = () => {
            console.log('✅ WebSocket connected');
            $connStatus.className = 'connection-status connected';
            $connText.textContent = 'Connected';

            // Clear reconnect timer
            if (wsReconnectTimer) {
                clearTimeout(wsReconnectTimer);
                wsReconnectTimer = null;
            }
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                handleWebSocketMessage(message);
            } catch (e) {
                console.warn('Invalid WebSocket message:', event.data);
            }
        };

        ws.onclose = () => {
            console.log('🔌 WebSocket disconnected');
            $connStatus.className = 'connection-status disconnected';
            $connText.textContent = 'Disconnected';

            // Auto-reconnect after 3 seconds
            wsReconnectTimer = setTimeout(() => {
                console.log('🔄 Attempting WebSocket reconnect...');
                $connText.textContent = 'Reconnecting...';
                connectWebSocket();
            }, 3000);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    } catch (err) {
        console.error('Failed to create WebSocket:', err);
        $connStatus.className = 'connection-status disconnected';
        $connText.textContent = 'Error';
    }
}

/**
 * Handle incoming WebSocket messages.
 *
 * Message types:
 *   - device_update: A device's state or brightness changed
 *   - device_added: A new device was added
 *   - device_deleted: A device was removed
 *   - pong: Response to our ping (keepalive)
 */
function handleWebSocketMessage(message) {
    switch (message.type) {
        case 'device_update': {
            const updated = message.data;
            const idx = devices.findIndex(d => d.id === updated.id);
            if (idx !== -1) {
                devices[idx] = updated;
                renderDevices();

                // Flash animation on the updated card
                const card = document.getElementById(`device-card-${updated.id}`);
                if (card) {
                    card.classList.add('just-updated');
                    setTimeout(() => card.classList.remove('just-updated'), 700);
                }

                showToast(
                    updated.state === 'on' ? '🟢' : '🔴',
                    `${updated.name} turned ${updated.state.toUpperCase()}`
                );
            }
            break;
        }

        case 'device_added': {
            devices.push(message.data);
            renderDevices();
            showToast('➕', `New device added: ${message.data.name}`);
            break;
        }

        case 'device_deleted': {
            devices = devices.filter(d => d.id !== message.data.id);
            renderDevices();
            showToast('🗑️', `Device removed`);
            break;
        }

        case 'pong':
            // Keepalive response — nothing to do
            break;

        default:
            console.log('Unknown WebSocket message type:', message.type);
    }
}

// Send periodic pings to keep the connection alive
setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
    }
}, 30000);

// ═══════════════════════════════════════════════════════════════════════════════
// ACTIVITY LOG PANEL
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Render the activity log panel with recent actions.
 */
async function renderLogs() {
    const logs = await fetchLogs();

    if (logs.length === 0) {
        $logList.innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:40px 0;">No activity yet</p>';
        return;
    }

    $logList.innerHTML = logs.map(log => {
        const dotClass = log.new_state === 'on' ? 'on' : log.new_state === 'off' ? 'off' : 'other';
        const deviceName = log.device_name || `Device #${log.device_id}`;
        const timeStr = log.timestamp ? new Date(log.timestamp).toLocaleString() : '';
        const actionText = log.action === 'state_change'
            ? `${log.old_state} → ${log.new_state}`
            : `${log.action}: ${log.old_state} → ${log.new_state}`;

        return `
            <div class="log-entry">
                <span class="log-dot ${dotClass}"></span>
                <div class="log-info">
                    <div class="log-device">${deviceName}</div>
                    <div class="log-action">${actionText}</div>
                    <div class="log-time">${timeStr}</div>
                </div>
                <span class="log-source">${log.source}</span>
            </div>
        `;
    }).join('');
}

// Log panel open/close
document.getElementById('btn-open-log').addEventListener('click', async () => {
    $logPanel.classList.add('open');
    await renderLogs();
});

document.getElementById('btn-close-log').addEventListener('click', () => {
    $logPanel.classList.remove('open');
});

// ═══════════════════════════════════════════════════════════════════════════════
// TOAST NOTIFICATIONS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Show a temporary toast notification.
 */
function showToast(icon, message, duration = 3500) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<span class="toast-icon">${icon}</span><span>${message}</span>`;
    $toastContainer.appendChild(toast);

    // Auto-remove after duration
    setTimeout(() => {
        toast.classList.add('toast-exit');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ═══════════════════════════════════════════════════════════════════════════════
// THEME TOGGLE
// ═══════════════════════════════════════════════════════════════════════════════

const $themeToggle = document.getElementById('btn-theme-toggle');

function initTheme() {
    const saved = localStorage.getItem('theme');
    if (saved) {
        document.documentElement.setAttribute('data-theme', saved);
    }
    // Default is dark (no data-theme attribute needed)
}

$themeToggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'light' ? 'dark' : 'light';

    if (next === 'dark') {
        document.documentElement.removeAttribute('data-theme');
    } else {
        document.documentElement.setAttribute('data-theme', next);
    }

    localStorage.setItem('theme', next);
});

// ═══════════════════════════════════════════════════════════════════════════════
// INITIALIZATION
// ═══════════════════════════════════════════════════════════════════════════════

async function init() {
    console.log('🏠 Smart Home Dashboard initializing...');

    // Apply saved theme
    initTheme();

    // Fetch devices from API
    devices = await fetchDevices();

    // Render the UI
    renderDevices();

    // Connect WebSocket for real-time updates
    connectWebSocket();

    console.log(`✅ Dashboard ready. ${devices.length} devices loaded.`);
}

// Start the app when the DOM is ready
document.addEventListener('DOMContentLoaded', init);
