/**
 * Feedback Implementation
 *
 * Handles LED and haptic motor patterns for user feedback.
 */

#include "feedback.h"

// ============================================================================
// State
// ============================================================================

// Current pattern state
static bool pattern_active = false;
static FeedbackType current_pattern = FEEDBACK_NONE;
static uint32_t pattern_start_time = 0;
static uint8_t pattern_step = 0;
static float pattern_intensity = 1.0f;

// Global brightness
static float global_brightness = 1.0f;

// Current LED state
static LEDColor current_color = COLOR_OFF;

// ============================================================================
// Pattern Definitions
// ============================================================================

// Pattern step structure
struct PatternStep {
    LEDColor color;
    uint8_t haptic;     // 0-255
    uint16_t duration;  // ms
};

// Maximum steps in a pattern
#define MAX_PATTERN_STEPS 8

// Pattern sequences
static const PatternStep pattern_session_start[] = {
    {COLOR_GREEN, 200, 100},
    {COLOR_GREEN, 0, 100},
    {COLOR_GREEN, 150, 80},
    {COLOR_OFF, 0, 0}
};

static const PatternStep pattern_session_end[] = {
    {COLOR_OFF, 200, 100},
    {COLOR_OFF, 0, 100},
    {COLOR_OFF, 200, 100},
    {COLOR_OFF, 0, 0}
};

static const PatternStep pattern_good_turn[] = {
    {COLOR_GREEN, 0, 150},
    {COLOR_OFF, 0, 0}
};

static const PatternStep pattern_missed_opp[] = {
    {COLOR_OFF, 180, 200},
    {COLOR_OFF, 0, 100},
    {COLOR_OFF, 120, 150},
    {COLOR_OFF, 0, 0}
};

static const PatternStep pattern_low_battery[] = {
    {COLOR_YELLOW, 0, 300},
    {COLOR_OFF, 0, 200},
    {COLOR_YELLOW, 0, 300},
    {COLOR_OFF, 0, 0}
};

static const PatternStep pattern_connected[] = {
    {COLOR_BLUE, 100, 200},
    {COLOR_OFF, 0, 0}
};

static const PatternStep pattern_disconnected[] = {
    {COLOR_RED, 100, 200},
    {COLOR_OFF, 0, 0}
};

static const PatternStep pattern_error[] = {
    {COLOR_RED, 255, 200},
    {COLOR_OFF, 0, 100},
    {COLOR_RED, 255, 200},
    {COLOR_OFF, 0, 0}
};

// ============================================================================
// Private Functions
// ============================================================================

/**
 * Apply brightness to a color
 */
static LEDColor apply_brightness(LEDColor color) {
    return {
        (uint8_t)(color.r * global_brightness),
        (uint8_t)(color.g * global_brightness),
        (uint8_t)(color.b * global_brightness)
    };
}

/**
 * Set LED PWM values
 */
static void set_led_pwm(LEDColor color) {
    LEDColor adjusted = apply_brightness(color);
    ledcWrite(PWM_CHANNEL_R, adjusted.r);
    ledcWrite(PWM_CHANNEL_G, adjusted.g);
    ledcWrite(PWM_CHANNEL_B, adjusted.b);
    current_color = color;
}

/**
 * Set haptic PWM value
 */
static void set_haptic_pwm(uint8_t value, float intensity) {
    uint8_t adjusted = (uint8_t)(value * intensity);
    ledcWrite(PWM_CHANNEL_HAPTIC, adjusted);
}

/**
 * Get pattern steps for a feedback type
 */
static const PatternStep* get_pattern_steps(FeedbackType type) {
    switch (type) {
        case FEEDBACK_SESSION_START:  return pattern_session_start;
        case FEEDBACK_SESSION_END:    return pattern_session_end;
        case FEEDBACK_GOOD_TURN:      return pattern_good_turn;
        case FEEDBACK_MISSED_OPP:     return pattern_missed_opp;
        case FEEDBACK_LOW_BATTERY:    return pattern_low_battery;
        case FEEDBACK_CONNECTED:      return pattern_connected;
        case FEEDBACK_DISCONNECTED:   return pattern_disconnected;
        case FEEDBACK_ERROR:          return pattern_error;
        default:                      return nullptr;
    }
}

/**
 * Count steps in a pattern (until duration == 0)
 */
static uint8_t count_pattern_steps(const PatternStep* steps) {
    if (!steps) return 0;

    uint8_t count = 0;
    while (count < MAX_PATTERN_STEPS && steps[count].duration > 0) {
        count++;
    }
    return count;
}

// ============================================================================
// Public Functions
// ============================================================================

void feedback_init() {
    Serial.println("Initializing feedback...");

    // Configure LED PWM channels
    ledcSetup(PWM_CHANNEL_R, PWM_FREQ, PWM_RESOLUTION);
    ledcSetup(PWM_CHANNEL_G, PWM_FREQ, PWM_RESOLUTION);
    ledcSetup(PWM_CHANNEL_B, PWM_FREQ, PWM_RESOLUTION);
    ledcSetup(PWM_CHANNEL_HAPTIC, PWM_FREQ, PWM_RESOLUTION);

    // Attach pins to channels
    ledcAttachPin(LED_PIN_R, PWM_CHANNEL_R);
    ledcAttachPin(LED_PIN_G, PWM_CHANNEL_G);
    ledcAttachPin(LED_PIN_B, PWM_CHANNEL_B);
    ledcAttachPin(HAPTIC_PIN, PWM_CHANNEL_HAPTIC);

    // Start with everything off
    feedback_led_off();
    feedback_haptic_off();

    Serial.println("Feedback initialized");
}

void feedback_trigger(FeedbackType type, float intensity) {
    // Cancel any active pattern
    feedback_cancel();

    if (type == FEEDBACK_NONE) {
        return;
    }

    const PatternStep* steps = get_pattern_steps(type);
    if (!steps) {
        return;
    }

    pattern_active = true;
    current_pattern = type;
    pattern_start_time = millis();
    pattern_step = 0;
    pattern_intensity = constrain(intensity, 0.0f, 1.0f);

    // Apply first step immediately
    set_led_pwm(steps[0].color);
    set_haptic_pwm(steps[0].haptic, pattern_intensity);

    Serial.printf("Feedback triggered: %d (intensity: %.2f)\n", type, intensity);
}

void feedback_set_led(LEDColor color) {
    set_led_pwm(color);
}

void feedback_set_led_rgb(uint8_t r, uint8_t g, uint8_t b) {
    LEDColor color = {r, g, b};
    set_led_pwm(color);
}

void feedback_led_off() {
    set_led_pwm(COLOR_OFF);
}

void feedback_haptic(float intensity, uint16_t duration_ms) {
    intensity = constrain(intensity, 0.0f, 1.0f);
    uint8_t pwm = (uint8_t)(255 * intensity);
    set_haptic_pwm(pwm, 1.0f);

    // Non-blocking: caller should use feedback_process() or delay
    // For simple blocking buzz:
    if (duration_ms > 0) {
        delay(duration_ms);
        feedback_haptic_off();
    }
}

void feedback_haptic_off() {
    ledcWrite(PWM_CHANNEL_HAPTIC, 0);
}

bool feedback_is_active() {
    return pattern_active;
}

void feedback_process() {
    if (!pattern_active) {
        return;
    }

    const PatternStep* steps = get_pattern_steps(current_pattern);
    if (!steps) {
        feedback_cancel();
        return;
    }

    uint8_t total_steps = count_pattern_steps(steps);

    // Check if current step is complete
    uint32_t elapsed = millis() - pattern_start_time;
    uint32_t step_end = 0;

    for (uint8_t i = 0; i <= pattern_step && i < total_steps; i++) {
        step_end += steps[i].duration;
    }

    if (elapsed >= step_end) {
        pattern_step++;

        if (pattern_step >= total_steps) {
            // Pattern complete
            feedback_cancel();
            return;
        }

        // Apply next step
        set_led_pwm(steps[pattern_step].color);
        set_haptic_pwm(steps[pattern_step].haptic, pattern_intensity);
    }
}

void feedback_cancel() {
    pattern_active = false;
    current_pattern = FEEDBACK_NONE;
    pattern_step = 0;

    feedback_led_off();
    feedback_haptic_off();
}

void feedback_set_brightness(float brightness) {
    global_brightness = constrain(brightness, 0.0f, 1.0f);

    // Re-apply current color with new brightness
    if (current_color.r > 0 || current_color.g > 0 || current_color.b > 0) {
        set_led_pwm(current_color);
    }
}
