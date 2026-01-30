/**
 * Pitch Detection Implementation
 *
 * YIN algorithm for fundamental frequency estimation.
 * Simplified and optimized for ESP32.
 *
 * Reference: "YIN, a fundamental frequency estimator for speech and music"
 * de Cheveigné & Kawahara, 2002
 */

#include "pitch_detector.h"
#include <math.h>

// ============================================================================
// Private
// ============================================================================

// Buffer for YIN difference function (reused to save memory)
static float diff_buffer[256];  // Enough for tau_max at 16kHz

/**
 * YIN difference function (step 2)
 * d(tau) = sum((x[j] - x[j+tau])^2)
 */
static void yin_difference(const int16_t* samples, size_t count, float* diff, size_t tau_max) {
    size_t length = count - tau_max;

    diff[0] = 0;

    for (size_t tau = 1; tau < tau_max; tau++) {
        float sum = 0;
        for (size_t j = 0; j < length; j++) {
            float delta = (float)samples[j] - (float)samples[j + tau];
            sum += delta * delta;
        }
        diff[tau] = sum;
    }
}

/**
 * Cumulative mean normalized difference (step 3)
 * d'(tau) = d(tau) / ((1/tau) * sum(d(1..tau)))
 */
static void yin_cumulative_mean(float* diff, size_t tau_max) {
    diff[0] = 1.0f;

    float running_sum = 0;

    for (size_t tau = 1; tau < tau_max; tau++) {
        running_sum += diff[tau];
        if (running_sum > 0) {
            diff[tau] = diff[tau] * tau / running_sum;
        } else {
            diff[tau] = 1.0f;
        }
    }
}

/**
 * Find the first minimum below threshold (step 4)
 */
static int yin_absolute_threshold(const float* diff, size_t tau_min, size_t tau_max, float threshold) {
    // Find first value below threshold that is a local minimum
    for (size_t tau = tau_min; tau < tau_max - 1; tau++) {
        if (diff[tau] < threshold) {
            // Check if local minimum
            if (diff[tau] < diff[tau - 1] && diff[tau] <= diff[tau + 1]) {
                return tau;
            }
        }
    }

    // No value below threshold - find global minimum
    float min_val = diff[tau_min];
    size_t min_tau = tau_min;

    for (size_t tau = tau_min + 1; tau < tau_max; tau++) {
        if (diff[tau] < min_val) {
            min_val = diff[tau];
            min_tau = tau;
        }
    }

    // Only return if reasonably confident
    if (min_val < 0.5f) {
        return min_tau;
    }

    return -1;  // No pitch found
}

/**
 * Parabolic interpolation for sub-sample accuracy (step 5)
 */
static float yin_parabolic_interpolation(const float* diff, int tau, size_t tau_max) {
    if (tau <= 0 || tau >= (int)tau_max - 1) {
        return (float)tau;
    }

    float s0 = diff[tau - 1];
    float s1 = diff[tau];
    float s2 = diff[tau + 1];

    float adjustment = (s2 - s0) / (2.0f * (2.0f * s1 - s2 - s0 + 1e-10f));

    return (float)tau + adjustment;
}

// ============================================================================
// Public Functions
// ============================================================================

void pitch_init() {
    // Clear buffer
    memset(diff_buffer, 0, sizeof(diff_buffer));
    Serial.println("Pitch detector initialized");
}

PitchResult pitch_estimate(const int16_t* samples, size_t count, uint32_t sample_rate) {
    PitchResult result = {
        .valid = false,
        .pitch_hz = 0.0f,
        .confidence = 0.0f,
        .speaker = SPEAKER_UNKNOWN
    };

    // Calculate tau range from pitch range
    size_t tau_min = sample_rate / PITCH_MAX_HZ;  // ~32 for 500Hz at 16kHz
    size_t tau_max = sample_rate / PITCH_MIN_HZ;  // ~213 for 75Hz at 16kHz

    // Sanity checks
    if (tau_max > 255) tau_max = 255;  // Buffer limit
    if (count < tau_max * 2) {
        return result;  // Not enough samples
    }

    // Check if signal has enough energy
    int64_t energy = 0;
    for (size_t i = 0; i < count; i++) {
        energy += (int32_t)samples[i] * samples[i];
    }
    float rms = sqrt((float)energy / count) / 32768.0f;
    if (rms < 0.01f) {
        return result;  // Too quiet
    }

    // YIN step 2: Difference function
    yin_difference(samples, count, diff_buffer, tau_max);

    // YIN step 3: Cumulative mean normalized difference
    yin_cumulative_mean(diff_buffer, tau_max);

    // YIN step 4: Absolute threshold
    int tau = yin_absolute_threshold(diff_buffer, tau_min, tau_max, YIN_THRESHOLD);

    if (tau < 0) {
        return result;  // No pitch found (unvoiced)
    }

    // YIN step 5: Parabolic interpolation
    float tau_refined = yin_parabolic_interpolation(diff_buffer, tau, tau_max);

    if (tau_refined <= 0) {
        return result;
    }

    // Convert tau to frequency
    result.pitch_hz = (float)sample_rate / tau_refined;
    result.valid = true;
    result.confidence = 1.0f - diff_buffer[tau];  // Lower diff = higher confidence
    result.speaker = pitch_classify(result.pitch_hz);

    return result;
}

PitchResult pitch_estimate_robust(const int16_t* samples, size_t count, uint32_t sample_rate) {
    // Use multiple windows and take median
    const size_t window_size = PITCH_WINDOW_SAMPLES;
    const size_t hop_size = window_size / 2;

    float pitches[16];
    size_t pitch_count = 0;

    for (size_t i = 0; i + window_size <= count && pitch_count < 16; i += hop_size) {
        PitchResult r = pitch_estimate(samples + i, window_size, sample_rate);
        if (r.valid && r.pitch_hz > PITCH_MIN_HZ && r.pitch_hz < PITCH_MAX_HZ) {
            pitches[pitch_count++] = r.pitch_hz;
        }
    }

    PitchResult result = {
        .valid = false,
        .pitch_hz = 0.0f,
        .confidence = 0.0f,
        .speaker = SPEAKER_UNKNOWN
    };

    if (pitch_count == 0) {
        return result;
    }

    // Simple median (sort and pick middle)
    // Bubble sort is fine for <16 elements
    for (size_t i = 0; i < pitch_count - 1; i++) {
        for (size_t j = 0; j < pitch_count - i - 1; j++) {
            if (pitches[j] > pitches[j + 1]) {
                float tmp = pitches[j];
                pitches[j] = pitches[j + 1];
                pitches[j + 1] = tmp;
            }
        }
    }

    result.pitch_hz = pitches[pitch_count / 2];
    result.valid = true;
    result.confidence = (float)pitch_count / 8.0f;  // More estimates = more confident
    if (result.confidence > 1.0f) result.confidence = 1.0f;
    result.speaker = pitch_classify(result.pitch_hz);

    return result;
}

SpeakerType pitch_classify(float pitch_hz) {
    if (pitch_hz <= 0) {
        return SPEAKER_UNKNOWN;
    }
    if (pitch_hz >= PITCH_CHILD_THRESHOLD_HZ) {
        return SPEAKER_CHILD;
    }
    return SPEAKER_ADULT;
}

const char* speaker_type_str(SpeakerType type) {
    switch (type) {
        case SPEAKER_CHILD: return "child";
        case SPEAKER_ADULT: return "adult";
        default: return "unknown";
    }
}
