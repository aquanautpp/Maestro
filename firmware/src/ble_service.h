/**
 * BLE Service Module
 *
 * Provides BLE GATT service for communication with mobile app.
 *
 * Service Structure:
 *   - Service UUID: 12345678-1234-5678-1234-56789abcdef0
 *     - session_control (write): Start/stop recording session
 *     - event_stream (notify): Stream events to app
 *     - device_status (read): Battery, uptime, etc.
 */

#ifndef BLE_SERVICE_H
#define BLE_SERVICE_H

#include <Arduino.h>

// ============================================================================
// UUIDs (must match mobile app)
// ============================================================================

#define SERVICE_UUID           "12345678-1234-5678-1234-56789abcdef0"
#define CHAR_SESSION_CTRL_UUID "12345678-1234-5678-1234-56789abcdef1"
#define CHAR_EVENT_STREAM_UUID "12345678-1234-5678-1234-56789abcdef2"
#define CHAR_DEVICE_STATUS_UUID "12345678-1234-5678-1234-56789abcdef3"

// ============================================================================
// Event Types (for event_stream characteristic)
// ============================================================================

enum BLEEventType {
    BLE_EVENT_SERVE = 1,              // Child initiated
    BLE_EVENT_RETURN = 2,             // Adult responded
    BLE_EVENT_MISSED_OPPORTUNITY = 3  // Long silence after child
};

// ============================================================================
// Types
// ============================================================================

/**
 * Event data structure (sent via event_stream)
 * Serialized as JSON over BLE
 */
struct BLEEvent {
    BLEEventType type;
    float timestamp;          // Seconds since session start
    float confidence;         // 0.0 - 1.0
    float pitch_hz;          // Estimated pitch (optional)
    float response_latency;  // For RETURN events (seconds)
    float silence_duration;  // For MISSED_OPPORTUNITY events (seconds)
};

/**
 * Device status structure (read via device_status)
 */
struct DeviceStatus {
    uint8_t battery_percent;  // 0-100
    bool is_charging;
    uint32_t uptime_seconds;
    bool session_active;
    uint16_t events_in_session;
};

/**
 * Callback type for session control commands
 */
typedef void (*SessionControlCallback)(bool start);

/**
 * Callback type for connection state changes
 */
typedef void (*ConnectionCallback)(bool connected);

// ============================================================================
// Public Functions
// ============================================================================

/**
 * Initialize BLE service.
 * Sets up GATT server with characteristics.
 *
 * @param device_name Device name (e.g., "ECC-001")
 * @return true if initialization successful
 */
bool ble_init(const char* device_name);

/**
 * Start BLE advertising.
 * Call after init to make device discoverable.
 */
void ble_start_advertising();

/**
 * Stop BLE advertising.
 */
void ble_stop_advertising();

/**
 * Check if a client is connected.
 *
 * @return true if connected
 */
bool ble_is_connected();

/**
 * Send an event to connected client.
 * Event is JSON-encoded and sent via notification.
 *
 * @param event Event to send
 * @return true if sent successfully
 */
bool ble_send_event(const BLEEvent& event);

/**
 * Update device status.
 * Updates the device_status characteristic.
 *
 * @param status Current device status
 */
void ble_update_status(const DeviceStatus& status);

/**
 * Set callback for session control commands.
 *
 * @param callback Function to call when start/stop received
 */
void ble_set_session_callback(SessionControlCallback callback);

/**
 * Set callback for connection state changes.
 *
 * @param callback Function to call on connect/disconnect
 */
void ble_set_connection_callback(ConnectionCallback callback);

/**
 * Process BLE events.
 * Call periodically from main loop.
 */
void ble_process();

/**
 * Get number of connected clients.
 *
 * @return Number of connections (0 or 1 for BLE)
 */
uint8_t ble_connection_count();

#endif // BLE_SERVICE_H
