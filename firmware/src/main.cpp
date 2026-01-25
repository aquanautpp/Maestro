/**
 * Early Childhood Coach - Firmware
 *
 * Main entry point for the ESP32-S3 wearable device.
 *
 * This firmware:
 * 1. Captures audio continuously from INMP441 microphone
 * 2. Runs Voice Activity Detection to identify speech
 * 3. Detects conversational patterns (serve, return, missed opportunity)
 * 4. Provides haptic/LED feedback for missed opportunities
 * 5. Streams events to mobile app via BLE
 *
 * Hardware:
 * - ESP32-S3 DevKitC-1
 * - INMP441 I2S MEMS microphone
 * - RGB LED (optional)
 * - ERM vibration motor with transistor driver
 */

#include <Arduino.h>
#include "audio_capture.h"
#include "vad_detector.h"
#include "ble_service.h"
#include "feedback.h"

// ============================================================================
// Configuration
// ============================================================================

// Device identification
#define DEVICE_ID       "001"
#define DEVICE_NAME     "ECC-" DEVICE_ID

// Conversation detection thresholds
#define RESPONSE_THRESHOLD_MS     3000   // Max time for response to count as "return"
#define MISSED_OPP_THRESHOLD_MS   5000   // Silence duration for "missed opportunity"

// Status update interval
#define STATUS_UPDATE_INTERVAL_MS 5000

// Debug output
#define DEBUG_PRINT_INTERVAL_MS   1000

// ============================================================================
// State
// ============================================================================

// Session state
static bool session_active = false;
static uint32_t session_start_time = 0;
static uint16_t session_event_count = 0;

// Last speech detection
static bool last_was_speaking = false;
static uint32_t last_speech_end_time = 0;
static bool waiting_for_response = false;
static uint32_t child_speech_time = 0;

// For simple speaker classification (placeholder)
// In reality, this would use pitch estimation
static bool last_was_child = false;

// Timing
static uint32_t last_status_update = 0;
static uint32_t last_debug_print = 0;

// ============================================================================
// Forward Declarations
// ============================================================================

void on_session_control(bool start);
void on_ble_connection(bool connected);
void process_speech_segment(const SpeechSegment& segment);
void check_missed_opportunity();
void send_event(BLEEventType type, float extra_data = 0.0f);
float get_session_timestamp();
uint8_t estimate_battery();

// ============================================================================
// Setup
// ============================================================================

void setup() {
    // Initialize serial for debugging
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n\n====================================");
    Serial.println("Early Childhood Coach - Firmware");
    Serial.println("====================================\n");

    // Initialize subsystems
    Serial.println("Initializing subsystems...\n");

    // 1. Feedback (LED + haptic)
    feedback_init();
    feedback_trigger(FEEDBACK_SESSION_START, 0.3f);  // Brief startup indication
    delay(300);

    // 2. Audio capture
    if (!audio_init()) {
        Serial.println("FATAL: Audio init failed!");
        feedback_trigger(FEEDBACK_ERROR, 1.0f);
        while (1) { delay(1000); }
    }

    // 3. VAD
    vad_init();
    vad_set_adaptive(true);  // Enable adaptive threshold

    // 4. BLE
    if (!ble_init(DEVICE_NAME)) {
        Serial.println("FATAL: BLE init failed!");
        feedback_trigger(FEEDBACK_ERROR, 1.0f);
        while (1) { delay(1000); }
    }

    // Set BLE callbacks
    ble_set_session_callback(on_session_control);
    ble_set_connection_callback(on_ble_connection);

    // Start BLE advertising
    ble_start_advertising();

    Serial.println("\n====================================");
    Serial.println("Initialization complete!");
    Serial.printf("Device name: %s\n", DEVICE_NAME);
    Serial.println("Waiting for BLE connection...");
    Serial.println("====================================\n");

    // Ready indication
    feedback_trigger(FEEDBACK_CONNECTED, 0.5f);
}

// ============================================================================
// Main Loop
// ============================================================================

void loop() {
    uint32_t now = millis();

    // Process feedback patterns
    feedback_process();

    // Process BLE events
    ble_process();

    // Process audio capture (fills buffers)
    audio_process();

    // Only process VAD and events when session is active
    if (session_active) {
        // Get audio frame
        AudioFrame frame;
        if (audio_get_frame(&frame)) {
            // Run VAD
            VADResult vad_result = vad_process(&frame);

            // Check for speech segment end
            SpeechSegment segment;
            if (vad_get_segment(&segment)) {
                process_speech_segment(segment);
            }

            // Track speaking state transitions
            if (vad_result.is_speech && !last_was_speaking) {
                // Speech started
                Serial.println("Speech started");
            } else if (!vad_result.is_speech && last_was_speaking) {
                // Speech ended
                Serial.println("Speech ended");
                last_speech_end_time = now;
            }

            last_was_speaking = vad_result.is_speech;
        }

        // Check for missed opportunity
        check_missed_opportunity();
    }

    // Periodic status update to app
    if (now - last_status_update > STATUS_UPDATE_INTERVAL_MS) {
        DeviceStatus status = {
            .battery_percent = estimate_battery(),
            .is_charging = false,
            .uptime_seconds = now / 1000,
            .session_active = session_active,
            .events_in_session = session_event_count
        };
        ble_update_status(status);
        last_status_update = now;
    }

    // Debug output
    if (now - last_debug_print > DEBUG_PRINT_INTERVAL_MS) {
        if (session_active) {
            float level = audio_get_level();
            Serial.printf("Audio level: %.3f | VAD threshold: %.3f | Silence: %lu ms\n",
                         level, vad_get_threshold(), vad_silence_duration());
        }
        last_debug_print = now;
    }

    // Small delay to prevent watchdog issues
    delay(1);
}

// ============================================================================
// Callbacks
// ============================================================================

/**
 * Called when app sends start/stop command
 */
void on_session_control(bool start) {
    if (start && !session_active) {
        // Start session
        Serial.println("\n*** SESSION STARTED ***\n");

        session_active = true;
        session_start_time = millis();
        session_event_count = 0;

        // Reset state
        last_was_speaking = false;
        last_speech_end_time = 0;
        waiting_for_response = false;
        last_was_child = false;

        // Reset VAD
        vad_reset();

        // Start audio capture
        audio_start();

        // Feedback
        feedback_trigger(FEEDBACK_SESSION_START, 1.0f);

    } else if (!start && session_active) {
        // Stop session
        Serial.println("\n*** SESSION ENDED ***\n");

        session_active = false;

        // Stop audio capture
        audio_stop();

        // Feedback
        feedback_trigger(FEEDBACK_SESSION_END, 1.0f);
    }
}

/**
 * Called when BLE connects/disconnects
 */
void on_ble_connection(bool connected) {
    if (connected) {
        Serial.println("App connected");
        feedback_trigger(FEEDBACK_CONNECTED, 0.5f);
    } else {
        Serial.println("App disconnected");
        feedback_trigger(FEEDBACK_DISCONNECTED, 0.5f);

        // Auto-stop session on disconnect
        if (session_active) {
            on_session_control(false);
        }
    }
}

// ============================================================================
// Event Processing
// ============================================================================

/**
 * Process a completed speech segment
 */
void process_speech_segment(const SpeechSegment& segment) {
    uint32_t now = millis();

    // Simple speaker classification based on segment characteristics
    // In a real implementation, this would use pitch estimation
    // For now, we'll alternate or use energy heuristics

    // Heuristic: Higher energy = likely adult
    // This is a placeholder - real implementation needs pitch analysis
    bool is_child = (segment.avg_energy < 0.1f);

    Serial.printf("Speech segment: %lu ms, energy: %.3f, speaker: %s\n",
                  segment.duration_ms, segment.avg_energy,
                  is_child ? "child" : "adult");

    if (is_child) {
        // Child spoke - this is a "serve"
        send_event(BLE_EVENT_SERVE);
        waiting_for_response = true;
        child_speech_time = segment.end_ms;
        last_was_child = true;

        Serial.println("Event: SERVE (child spoke)");

    } else if (waiting_for_response) {
        // Adult spoke after child - check if it's a "return"
        uint32_t response_time = segment.start_ms - child_speech_time;

        if (response_time <= RESPONSE_THRESHOLD_MS) {
            // Quick response - successful return!
            send_event(BLE_EVENT_RETURN, response_time / 1000.0f);
            feedback_trigger(FEEDBACK_GOOD_TURN, 0.3f);

            Serial.printf("Event: RETURN (response time: %lu ms)\n", response_time);
        }

        waiting_for_response = false;
        last_was_child = false;
    }
}

/**
 * Check if too much silence has passed (missed opportunity)
 */
void check_missed_opportunity() {
    if (!waiting_for_response) {
        return;
    }

    uint32_t silence = vad_silence_duration();

    if (silence >= MISSED_OPP_THRESHOLD_MS) {
        // Too long without response - missed opportunity
        send_event(BLE_EVENT_MISSED_OPPORTUNITY, silence / 1000.0f);
        feedback_trigger(FEEDBACK_MISSED_OPP, 0.7f);

        Serial.printf("Event: MISSED OPPORTUNITY (silence: %lu ms)\n", silence);

        waiting_for_response = false;
        last_was_child = false;
    }
}

/**
 * Send event to app via BLE
 */
void send_event(BLEEventType type, float extra_data) {
    BLEEvent event = {
        .type = type,
        .timestamp = get_session_timestamp(),
        .confidence = 0.8f,  // Placeholder
        .pitch_hz = 0.0f,    // Not implemented yet
        .response_latency = 0.0f,
        .silence_duration = 0.0f
    };

    if (type == BLE_EVENT_RETURN) {
        event.response_latency = extra_data;
    } else if (type == BLE_EVENT_MISSED_OPPORTUNITY) {
        event.silence_duration = extra_data;
    }

    if (ble_send_event(event)) {
        session_event_count++;
    }
}

// ============================================================================
// Utilities
// ============================================================================

/**
 * Get timestamp relative to session start (in seconds)
 */
float get_session_timestamp() {
    if (!session_active || session_start_time == 0) {
        return 0.0f;
    }
    return (millis() - session_start_time) / 1000.0f;
}

/**
 * Estimate battery percentage
 * This is a placeholder - real implementation would read ADC
 */
uint8_t estimate_battery() {
    // Read battery voltage via ADC (if connected)
    // For now, return a placeholder
    static uint8_t fake_battery = 100;

    // Slowly drain for demo purposes
    if (session_active && fake_battery > 20) {
        fake_battery--;
    }

    return fake_battery;
}
