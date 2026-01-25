/**
 * Voice Activity Detection Module
 *
 * Simple energy-based VAD for detecting speech.
 * Uses short-term energy and zero-crossing rate.
 */

#ifndef VAD_DETECTOR_H
#define VAD_DETECTOR_H

#include <Arduino.h>
#include "audio_capture.h"

// ============================================================================
// Configuration
// ============================================================================

// Energy threshold for speech detection (0.0 - 1.0)
// Lower = more sensitive, Higher = less false positives
#define VAD_DEFAULT_THRESHOLD   0.02f

// Minimum speech duration to count as valid (ms)
#define VAD_MIN_SPEECH_MS       100

// Minimum silence duration to end speech segment (ms)
#define VAD_MIN_SILENCE_MS      300

// Hangover time - keep speech state for this long after energy drops (ms)
#define VAD_HANGOVER_MS         200

// ============================================================================
// Types
// ============================================================================

/**
 * VAD state machine states
 */
enum VADState {
    VAD_STATE_SILENCE,      // No speech detected
    VAD_STATE_SPEECH,       // Speech in progress
    VAD_STATE_HANGOVER      // Short pause during speech
};

/**
 * Result from VAD processing
 */
struct VADResult {
    bool is_speech;         // Currently detecting speech
    float energy;           // Current frame energy (0.0 - 1.0)
    float threshold;        // Current threshold
    VADState state;         // Internal state
    uint32_t speech_start;  // Timestamp when speech started (0 if not speaking)
    uint32_t speech_duration_ms;  // Duration of current speech segment
};

/**
 * Speech segment info (when speech ends)
 */
struct SpeechSegment {
    uint32_t start_ms;      // Start timestamp
    uint32_t end_ms;        // End timestamp
    uint32_t duration_ms;   // Duration
    float avg_energy;       // Average energy during segment
};

// ============================================================================
// Public Functions
// ============================================================================

/**
 * Initialize VAD detector.
 * Must be called before processing.
 */
void vad_init();

/**
 * Set energy threshold for speech detection.
 *
 * @param threshold Value between 0.0 and 1.0
 */
void vad_set_threshold(float threshold);

/**
 * Get current threshold.
 *
 * @return Current threshold value
 */
float vad_get_threshold();

/**
 * Enable/disable adaptive threshold.
 * When enabled, threshold adjusts based on background noise.
 *
 * @param enabled true to enable
 */
void vad_set_adaptive(bool enabled);

/**
 * Process an audio frame through VAD.
 *
 * @param frame Audio frame to process
 * @return VAD result for this frame
 */
VADResult vad_process(const AudioFrame* frame);

/**
 * Check if a speech segment just ended.
 * Call after vad_process() to get segment info.
 *
 * @param segment Pointer to store segment info
 * @return true if a segment just ended
 */
bool vad_get_segment(SpeechSegment* segment);

/**
 * Reset VAD state.
 * Call when starting a new session.
 */
void vad_reset();

/**
 * Get time since last speech activity (ms).
 * Useful for detecting missed opportunities.
 *
 * @return Milliseconds since last speech, or 0 if currently speaking
 */
uint32_t vad_silence_duration();

#endif // VAD_DETECTOR_H
