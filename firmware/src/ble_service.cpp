/**
 * BLE Service Implementation
 *
 * Uses ESP32 Arduino BLE library for GATT server.
 */

#include "ble_service.h"
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// ============================================================================
// State
// ============================================================================

static BLEServer* pServer = nullptr;
static BLEService* pService = nullptr;
static BLECharacteristic* pSessionCtrl = nullptr;
static BLECharacteristic* pEventStream = nullptr;
static BLECharacteristic* pDeviceStatus = nullptr;

static bool device_connected = false;
static bool old_device_connected = false;

static SessionControlCallback session_callback = nullptr;
static ConnectionCallback connection_callback = nullptr;

// ============================================================================
// BLE Callbacks
// ============================================================================

/**
 * Server connection callbacks
 */
class ServerCallbacks : public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) override {
        device_connected = true;
        Serial.println("BLE client connected");
    }

    void onDisconnect(BLEServer* pServer) override {
        device_connected = false;
        Serial.println("BLE client disconnected");
    }
};

/**
 * Session control characteristic callbacks
 */
class SessionCtrlCallbacks : public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic* pCharacteristic) override {
        std::string value = pCharacteristic->getValue();

        if (value.length() > 0) {
            // Parse command: "start" or "stop"
            String cmd = String(value.c_str());
            cmd.toLowerCase();
            cmd.trim();

            Serial.printf("Session control received: %s\n", cmd.c_str());

            if (session_callback) {
                if (cmd == "start" || cmd == "1") {
                    session_callback(true);
                } else if (cmd == "stop" || cmd == "0") {
                    session_callback(false);
                }
            }
        }
    }
};

// ============================================================================
// Private Functions
// ============================================================================

/**
 * Convert BLEEvent to JSON string
 */
static String event_to_json(const BLEEvent& event) {
    String json = "{";

    // Type
    switch (event.type) {
        case BLE_EVENT_SERVE:
            json += "\"type\":\"serve\"";
            break;
        case BLE_EVENT_RETURN:
            json += "\"type\":\"return\"";
            break;
        case BLE_EVENT_MISSED_OPPORTUNITY:
            json += "\"type\":\"missed_opportunity\"";
            break;
    }

    // Timestamp
    json += ",\"timestamp\":";
    json += String(event.timestamp, 2);

    // Confidence
    json += ",\"confidence\":";
    json += String(event.confidence, 2);

    // Optional fields based on event type
    if (event.pitch_hz > 0) {
        json += ",\"pitch_hz\":";
        json += String(event.pitch_hz, 1);
    }

    if (event.type == BLE_EVENT_RETURN && event.response_latency > 0) {
        json += ",\"response_latency\":";
        json += String(event.response_latency, 2);
    }

    if (event.type == BLE_EVENT_MISSED_OPPORTUNITY && event.silence_duration > 0) {
        json += ",\"silence_duration\":";
        json += String(event.silence_duration, 2);
    }

    json += "}";
    return json;
}

/**
 * Convert DeviceStatus to JSON string
 */
static String status_to_json(const DeviceStatus& status) {
    String json = "{";
    json += "\"battery\":";
    json += String(status.battery_percent);
    json += ",\"charging\":";
    json += status.is_charging ? "true" : "false";
    json += ",\"uptime\":";
    json += String(status.uptime_seconds);
    json += ",\"session_active\":";
    json += status.session_active ? "true" : "false";
    json += ",\"events\":";
    json += String(status.events_in_session);
    json += "}";
    return json;
}

// ============================================================================
// Public Functions
// ============================================================================

bool ble_init(const char* device_name) {
    Serial.printf("Initializing BLE with name: %s\n", device_name);

    // Initialize BLE
    BLEDevice::init(device_name);

    // Create server
    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new ServerCallbacks());

    // Create service
    pService = pServer->createService(SERVICE_UUID);

    // Create characteristics

    // Session control (write)
    pSessionCtrl = pService->createCharacteristic(
        CHAR_SESSION_CTRL_UUID,
        BLECharacteristic::PROPERTY_WRITE
    );
    pSessionCtrl->setCallbacks(new SessionCtrlCallbacks());

    // Event stream (notify)
    pEventStream = pService->createCharacteristic(
        CHAR_EVENT_STREAM_UUID,
        BLECharacteristic::PROPERTY_NOTIFY
    );
    pEventStream->addDescriptor(new BLE2902());

    // Device status (read)
    pDeviceStatus = pService->createCharacteristic(
        CHAR_DEVICE_STATUS_UUID,
        BLECharacteristic::PROPERTY_READ
    );

    // Set initial status
    DeviceStatus initial_status = {
        .battery_percent = 100,
        .is_charging = false,
        .uptime_seconds = 0,
        .session_active = false,
        .events_in_session = 0
    };
    String status_json = status_to_json(initial_status);
    pDeviceStatus->setValue(status_json.c_str());

    // Start service
    pService->start();

    Serial.println("BLE service started");
    return true;
}

void ble_start_advertising() {
    BLEAdvertising* pAdvertising = BLEDevice::getAdvertising();

    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->setScanResponse(true);
    pAdvertising->setMinPreferred(0x06);  // Functions that help with iPhone connections
    pAdvertising->setMinPreferred(0x12);

    BLEDevice::startAdvertising();
    Serial.println("BLE advertising started");
}

void ble_stop_advertising() {
    BLEDevice::stopAdvertising();
    Serial.println("BLE advertising stopped");
}

bool ble_is_connected() {
    return device_connected;
}

bool ble_send_event(const BLEEvent& event) {
    if (!device_connected || !pEventStream) {
        return false;
    }

    String json = event_to_json(event);

    // Convert to base64 for reliable transmission
    // (or just send as UTF-8 for simplicity)
    pEventStream->setValue(json.c_str());
    pEventStream->notify();

    Serial.printf("BLE event sent: %s\n", json.c_str());
    return true;
}

void ble_update_status(const DeviceStatus& status) {
    if (!pDeviceStatus) {
        return;
    }

    String json = status_to_json(status);
    pDeviceStatus->setValue(json.c_str());
}

void ble_set_session_callback(SessionControlCallback callback) {
    session_callback = callback;
}

void ble_set_connection_callback(ConnectionCallback callback) {
    connection_callback = callback;
}

void ble_process() {
    // Handle connection state changes
    if (device_connected != old_device_connected) {
        if (connection_callback) {
            connection_callback(device_connected);
        }

        if (!device_connected) {
            // Restart advertising when disconnected
            delay(500);  // Give BLE stack time to settle
            ble_start_advertising();
        }

        old_device_connected = device_connected;
    }
}

uint8_t ble_connection_count() {
    return device_connected ? 1 : 0;
}
