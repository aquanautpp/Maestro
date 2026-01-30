/**
 * Pitch Detection Module
 *
 * Estimates fundamental frequency (F0) using YIN algorithm.
 * Used to classify speakers as adult (<280Hz) or child (>=280Hz).
 *
 * Optimized for ESP32 memory constraints.
 */

#ifndef PITCH_DETECTOR_H
#define PITCH_DETECTOR_H

#include <Arduino.h>

// ============================================================================
// Configuration
// ============================================================================

// Pitch detection range (Hz)
#define PITCH_MIN_HZ        75      // Lowest adult male
#define PITCH_MAX_HZ        500     // Highest child

// Classification threshold
#define PITCH_CHILD_THRESHOLD_HZ    280

// YIN algorithm threshold (lower = stricter voiced detection)
#define YIN_THRESHOLD       0.15f

// Analysis window (needs ~50ms of audio for good pitch estimate)
// At 16kHz, 50ms = 800 samples
#define PITCH_WINDOW_SAMPLES    800

// ============================================================================
// Types
// ============================================================================

/**
 * Speaker classification
 */
enum SpeakerType {
    SPEAKER_UNKNOWN,    // Could not determine pitch
    SPEAKER_ADULT,      // Pitch < 280Hz
    SPEAKER_CHILD       // Pitch >= 280Hz
};

/**
 * Pitch estimation result
 */
struct PitchResult {
    bool valid;             // Was pitch detected?
    float pitch_hz;         // Estimated pitch in Hz
    float confidence;       // Confidence 0-1 (lower YIN value = higher confidence)
    SpeakerType speaker;    // Classification
};

// ============================================================================
// Public Functions
// ============================================================================

/**
 * Initialize pitch detector.
 */
void pitch_init();

/**
 * Estimate pitch from audio samples.
 *
 * @param samples Audio samples (16-bit signed)
 * @param count Number of samples (should be >= PITCH_WINDOW_SAMPLES)
 * @param sample_rate Sample rate in Hz
 * @return Pitch estimation result
 */
PitchResult pitch_estimate(const int16_t* samples, size_t count, uint32_t sample_rate);

/**
 * Estimate pitch using median of multiple windows.
 * More robust than single estimate.
 *
 * @param samples Audio samples
 * @param count Number of samples
 * @param sample_rate Sample rate
 * @return Pitch estimation result
 */
PitchResult pitch_estimate_robust(const int16_t* samples, size_t count, uint32_t sample_rate);

/**
 * Classify speaker based on pitch.
 *
 * @param pitch_hz Pitch in Hz (0 if unknown)
 * @return Speaker type
 */
SpeakerType pitch_classify(float pitch_hz);

/**
 * Get speaker type as string.
 */
const char* speaker_type_str(SpeakerType type);

#endif // PITCH_DETECTOR_H
