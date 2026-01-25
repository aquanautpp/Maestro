/**
 * Voice Activity Detection Implementation
 *
 * Simple energy-based VAD with state machine for robust detection.
 */

#include "vad_detector.h"
#include <math.h>

// ============================================================================
// State
// ============================================================================

// Configuration
static float energy_threshold = VAD_DEFAULT_THRESHOLD;
static bool adaptive_enabled = false;

// State machine
static VADState current_state = VAD_STATE_SILENCE;
static uint32_t state_start_time = 0;
static uint32_t last_speech_time = 0;
static uint32_t speech_start_time = 0;

// Adaptive threshold
static float noise_floor = 0.01f;
static float noise_alpha = 0.995f;  // Slow adaptation

// Segment tracking
static SpeechSegment pending_segment;
static bool segment_ready = false;
static float segment_energy_sum = 0.0f;
static uint32_t segment_frame_count = 0;

// ============================================================================
// Private Functions
// ============================================================================

/**
 * Calculate frame energy (RMS normalized to 0-1)
 */
static float calculate_energy(const int16_t* samples, size_t count) {
    if (count == 0) return 0.0f;

    int64_t sum_squares = 0;
    for (size_t i = 0; i < count; i++) {
        int32_t s = samples[i];
        sum_squares += s * s;
    }

    float rms = sqrt((float)sum_squares / count);
    return rms / 32768.0f;
}

/**
 * Calculate zero-crossing rate (0-1, higher = more high frequency content)
 */
static float calculate_zcr(const int16_t* samples, size_t count) {
    if (count < 2) return 0.0f;

    uint32_t crossings = 0;
    for (size_t i = 1; i < count; i++) {
        if ((samples[i] >= 0 && samples[i-1] < 0) ||
            (samples[i] < 0 && samples[i-1] >= 0)) {
            crossings++;
        }
    }

    return (float)crossings / (count - 1);
}

/**
 * Update adaptive noise floor estimate
 */
static void update_noise_floor(float energy) {
    // Only update during silence
    if (current_state == VAD_STATE_SILENCE) {
        // Exponential moving average
        noise_floor = noise_alpha * noise_floor + (1.0f - noise_alpha) * energy;

        // Clamp to reasonable range
        if (noise_floor < 0.001f) noise_floor = 0.001f;
        if (noise_floor > 0.1f) noise_floor = 0.1f;
    }
}

/**
 * Get effective threshold (considering adaptive mode)
 */
static float get_effective_threshold() {
    if (adaptive_enabled) {
        // Threshold is noise floor plus margin
        return noise_floor * 3.0f;
    }
    return energy_threshold;
}

/**
 * Transition to a new state
 */
static void transition_to(VADState new_state, uint32_t now) {
    if (current_state == new_state) return;

    // Handle state exit
    if (current_state == VAD_STATE_SPEECH) {
        // Speech just ended - create segment
        pending_segment.end_ms = now;
        pending_segment.duration_ms = now - pending_segment.start_ms;

        if (segment_frame_count > 0) {
            pending_segment.avg_energy = segment_energy_sum / segment_frame_count;
        } else {
            pending_segment.avg_energy = 0.0f;
        }

        // Only report segments longer than minimum
        if (pending_segment.duration_ms >= VAD_MIN_SPEECH_MS) {
            segment_ready = true;
        }

        last_speech_time = now;
    }

    // Handle state enter
    if (new_state == VAD_STATE_SPEECH) {
        pending_segment.start_ms = now;
        segment_energy_sum = 0.0f;
        segment_frame_count = 0;
        speech_start_time = now;
    }

    current_state = new_state;
    state_start_time = now;
}

// ============================================================================
// Public Functions
// ============================================================================

void vad_init() {
    energy_threshold = VAD_DEFAULT_THRESHOLD;
    adaptive_enabled = false;
    current_state = VAD_STATE_SILENCE;
    state_start_time = millis();
    last_speech_time = 0;
    speech_start_time = 0;
    noise_floor = 0.01f;
    segment_ready = false;

    Serial.println("VAD initialized");
}

void vad_set_threshold(float threshold) {
    if (threshold < 0.001f) threshold = 0.001f;
    if (threshold > 1.0f) threshold = 1.0f;
    energy_threshold = threshold;
    Serial.printf("VAD threshold set to %.3f\n", threshold);
}

float vad_get_threshold() {
    return get_effective_threshold();
}

void vad_set_adaptive(bool enabled) {
    adaptive_enabled = enabled;
    if (enabled) {
        Serial.println("VAD adaptive mode enabled");
    }
}

VADResult vad_process(const AudioFrame* frame) {
    VADResult result = {
        .is_speech = false,
        .energy = 0.0f,
        .threshold = get_effective_threshold(),
        .state = current_state,
        .speech_start = 0,
        .speech_duration_ms = 0
    };

    if (!frame || !frame->valid) {
        return result;
    }

    uint32_t now = frame->timestamp_ms;

    // Calculate features
    float energy = calculate_energy(frame->samples, AUDIO_FRAME_SAMPLES);
    float zcr = calculate_zcr(frame->samples, AUDIO_FRAME_SAMPLES);

    result.energy = energy;

    // Update adaptive noise floor
    if (adaptive_enabled) {
        update_noise_floor(energy);
    }

    // Determine if this frame is speech
    float threshold = get_effective_threshold();
    bool frame_is_speech = (energy > threshold);

    // Also consider ZCR - speech typically has moderate ZCR
    // Very high ZCR might be noise, very low might be silence
    if (frame_is_speech && (zcr < 0.05f || zcr > 0.5f)) {
        // Suspicious ZCR, require higher energy
        frame_is_speech = (energy > threshold * 1.5f);
    }

    // State machine
    switch (current_state) {
        case VAD_STATE_SILENCE:
            if (frame_is_speech) {
                transition_to(VAD_STATE_SPEECH, now);
            }
            break;

        case VAD_STATE_SPEECH:
            // Accumulate energy for segment stats
            segment_energy_sum += energy;
            segment_frame_count++;

            if (!frame_is_speech) {
                // Start hangover period
                transition_to(VAD_STATE_HANGOVER, now);
            }
            break;

        case VAD_STATE_HANGOVER:
            if (frame_is_speech) {
                // Back to speech
                transition_to(VAD_STATE_SPEECH, now);
            } else if (now - state_start_time > VAD_HANGOVER_MS) {
                // Hangover expired - speech ended
                transition_to(VAD_STATE_SILENCE, now);
            }
            break;
    }

    // Fill result
    result.state = current_state;
    result.is_speech = (current_state == VAD_STATE_SPEECH ||
                        current_state == VAD_STATE_HANGOVER);
    result.threshold = threshold;

    if (result.is_speech) {
        result.speech_start = speech_start_time;
        result.speech_duration_ms = now - speech_start_time;
    }

    return result;
}

bool vad_get_segment(SpeechSegment* segment) {
    if (!segment_ready || !segment) {
        return false;
    }

    *segment = pending_segment;
    segment_ready = false;
    return true;
}

void vad_reset() {
    current_state = VAD_STATE_SILENCE;
    state_start_time = millis();
    last_speech_time = 0;
    speech_start_time = 0;
    segment_ready = false;
    segment_energy_sum = 0.0f;
    segment_frame_count = 0;

    Serial.println("VAD reset");
}

uint32_t vad_silence_duration() {
    if (current_state == VAD_STATE_SPEECH ||
        current_state == VAD_STATE_HANGOVER) {
        return 0;
    }

    if (last_speech_time == 0) {
        return 0;  // Never detected speech
    }

    return millis() - last_speech_time;
}
