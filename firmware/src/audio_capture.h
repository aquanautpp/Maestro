/**
 * Audio Capture Module
 *
 * Captures audio from INMP441 I2S MEMS microphone.
 * Maintains a circular buffer for continuous audio recording.
 *
 * Hardware connections (INMP441 -> ESP32-S3):
 *   - VDD  -> 3.3V
 *   - GND  -> GND
 *   - SD   -> GPIO 4  (I2S Data)
 *   - SCK  -> GPIO 5  (I2S Clock)
 *   - WS   -> GPIO 6  (I2S Word Select / LRCK)
 *   - L/R  -> GND     (Left channel)
 */

#ifndef AUDIO_CAPTURE_H
#define AUDIO_CAPTURE_H

#include <Arduino.h>

// ============================================================================
// Configuration
// ============================================================================

// I2S pins for INMP441
#define I2S_SD_PIN   4   // Serial Data
#define I2S_SCK_PIN  5   // Serial Clock
#define I2S_WS_PIN   6   // Word Select (LRCK)

// Audio format
#define AUDIO_SAMPLE_RATE   16000  // 16kHz
#define AUDIO_BITS          16     // 16-bit
#define AUDIO_CHANNELS      1      // Mono

// Buffer configuration
// 10 seconds of audio at 16kHz, 16-bit = 320,000 bytes
#define AUDIO_BUFFER_SECONDS    10
#define AUDIO_BUFFER_SIZE       (AUDIO_SAMPLE_RATE * AUDIO_BUFFER_SECONDS)

// Frame size for processing (30ms = 480 samples at 16kHz)
#define AUDIO_FRAME_SAMPLES     480
#define AUDIO_FRAME_MS          30

// ============================================================================
// Types
// ============================================================================

/**
 * Audio frame for processing
 */
struct AudioFrame {
    int16_t samples[AUDIO_FRAME_SAMPLES];
    uint32_t timestamp_ms;
    bool valid;
};

// ============================================================================
// Public Functions
// ============================================================================

/**
 * Initialize I2S peripheral and audio buffers.
 * Must be called before any other audio functions.
 *
 * @return true if initialization successful
 */
bool audio_init();

/**
 * Start audio capture.
 * Begins filling the circular buffer with audio data.
 */
void audio_start();

/**
 * Stop audio capture.
 * Pauses the I2S peripheral.
 */
void audio_stop();

/**
 * Check if audio capture is running.
 *
 * @return true if capturing
 */
bool audio_is_running();

/**
 * Get the next audio frame for processing.
 * Non-blocking - returns immediately with valid=false if no frame ready.
 *
 * @param frame Pointer to AudioFrame struct to fill
 * @return true if a valid frame was returned
 */
bool audio_get_frame(AudioFrame* frame);

/**
 * Get current audio level (for debugging/visualization).
 * Returns RMS amplitude of recent samples.
 *
 * @return RMS level (0.0 - 1.0)
 */
float audio_get_level();

/**
 * Get number of frames available for processing.
 *
 * @return Number of unprocessed frames
 */
uint32_t audio_frames_available();

/**
 * Process audio in the background.
 * Call this from loop() to keep buffers flowing.
 */
void audio_process();

#endif // AUDIO_CAPTURE_H
