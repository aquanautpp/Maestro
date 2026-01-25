/**
 * Feedback Module
 *
 * Controls LED and haptic motor for user feedback.
 *
 * Hardware connections:
 *   LED (WS2812B or simple RGB):
 *   - Data -> GPIO 48 (built-in RGB on some ESP32-S3 boards)
 *   - Or use simple RGB LED on GPIO 38, 39, 40
 *
 *   Haptic motor (ERM with transistor driver):
 *   - Control -> GPIO 7 (PWM capable)
 */

#ifndef FEEDBACK_H
#define FEEDBACK_H

#include <Arduino.h>

// ============================================================================
// Configuration
// ============================================================================

// LED pins (simple RGB LED)
#define LED_PIN_R       38
#define LED_PIN_G       39
#define LED_PIN_B       40

// Alternative: Use built-in RGB LED on GPIO 48 (some boards)
// #define LED_PIN_NEOPIXEL 48

// Haptic motor pin
#define HAPTIC_PIN      7

// PWM configuration
#define PWM_FREQ        5000
#define PWM_RESOLUTION  8   // 8-bit = 0-255

// PWM channels
#define PWM_CHANNEL_R   0
#define PWM_CHANNEL_G   1
#define PWM_CHANNEL_B   2
#define PWM_CHANNEL_HAPTIC 3

// ============================================================================
// Types
// ============================================================================

/**
 * Feedback types
 */
enum FeedbackType {
    FEEDBACK_NONE = 0,
    FEEDBACK_SESSION_START,     // Session started - short buzz, green
    FEEDBACK_SESSION_END,       // Session ended - double buzz, off
    FEEDBACK_GOOD_TURN,         // Successful turn - brief green pulse
    FEEDBACK_MISSED_OPP,        // Missed opportunity - gentle buzz
    FEEDBACK_LOW_BATTERY,       // Low battery warning - yellow flash
    FEEDBACK_CONNECTED,         // BLE connected - brief blue
    FEEDBACK_DISCONNECTED,      // BLE disconnected - brief red
    FEEDBACK_ERROR              // Error - red flash
};

/**
 * LED color
 */
struct LEDColor {
    uint8_t r;
    uint8_t g;
    uint8_t b;
};

// Predefined colors
const LEDColor COLOR_OFF     = {0, 0, 0};
const LEDColor COLOR_RED     = {255, 0, 0};
const LEDColor COLOR_GREEN   = {0, 255, 0};
const LEDColor COLOR_BLUE    = {0, 0, 255};
const LEDColor COLOR_YELLOW  = {255, 200, 0};
const LEDColor COLOR_CYAN    = {0, 255, 255};
const LEDColor COLOR_PURPLE  = {128, 0, 255};
const LEDColor COLOR_WHITE   = {255, 255, 255};

// ============================================================================
// Public Functions
// ============================================================================

/**
 * Initialize feedback hardware.
 * Sets up PWM for LED and haptic.
 */
void feedback_init();

/**
 * Trigger a feedback pattern.
 *
 * @param type Type of feedback
 * @param intensity Intensity 0.0-1.0 (affects haptic strength)
 */
void feedback_trigger(FeedbackType type, float intensity = 1.0f);

/**
 * Set LED color directly.
 *
 * @param color RGB color
 */
void feedback_set_led(LEDColor color);

/**
 * Set LED by individual RGB values (0-255).
 */
void feedback_set_led_rgb(uint8_t r, uint8_t g, uint8_t b);

/**
 * Turn off LED.
 */
void feedback_led_off();

/**
 * Trigger haptic with specific parameters.
 *
 * @param intensity Intensity 0.0-1.0
 * @param duration_ms Duration in milliseconds
 */
void feedback_haptic(float intensity, uint16_t duration_ms);

/**
 * Turn off haptic motor.
 */
void feedback_haptic_off();

/**
 * Check if feedback is currently playing.
 *
 * @return true if a feedback pattern is active
 */
bool feedback_is_active();

/**
 * Process feedback timing.
 * Call from main loop to handle timed patterns.
 */
void feedback_process();

/**
 * Cancel any active feedback.
 */
void feedback_cancel();

/**
 * Set global brightness for LED (0.0-1.0).
 * Useful for night mode or low-light conditions.
 *
 * @param brightness Brightness level
 */
void feedback_set_brightness(float brightness);

#endif // FEEDBACK_H
