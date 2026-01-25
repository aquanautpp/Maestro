/**
 * Audio Capture Implementation
 *
 * Uses ESP32-S3 I2S peripheral to capture audio from INMP441 microphone.
 * Implements a circular buffer for continuous recording.
 */

#include "audio_capture.h"
#include <driver/i2s.h>

// ============================================================================
// Constants
// ============================================================================

// I2S port to use
#define I2S_PORT I2S_NUM_0

// DMA buffer configuration
#define DMA_BUF_COUNT   8
#define DMA_BUF_LEN     1024

// ============================================================================
// State
// ============================================================================

// Circular buffer for audio samples
static int16_t audio_buffer[AUDIO_BUFFER_SIZE];
static volatile uint32_t write_index = 0;
static volatile uint32_t read_index = 0;

// Running state
static bool is_initialized = false;
static bool is_running = false;

// Recent level for visualization
static float current_level = 0.0f;

// ============================================================================
// Private Functions
// ============================================================================

/**
 * Configure I2S peripheral for INMP441 microphone
 */
static bool configure_i2s() {
    // I2S configuration
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = AUDIO_SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,  // INMP441 on left channel
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = DMA_BUF_COUNT,
        .dma_buf_len = DMA_BUF_LEN,
        .use_apll = false,
        .tx_desc_auto_clear = false,
        .fixed_mclk = 0
    };

    // Pin configuration
    i2s_pin_config_t pin_config = {
        .bck_io_num = I2S_SCK_PIN,
        .ws_io_num = I2S_WS_PIN,
        .data_out_num = I2S_PIN_NO_CHANGE,  // Not used for RX
        .data_in_num = I2S_SD_PIN
    };

    // Install I2S driver
    esp_err_t err = i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
    if (err != ESP_OK) {
        Serial.printf("I2S driver install failed: %d\n", err);
        return false;
    }

    // Set pin configuration
    err = i2s_set_pin(I2S_PORT, &pin_config);
    if (err != ESP_OK) {
        Serial.printf("I2S set pin failed: %d\n", err);
        i2s_driver_uninstall(I2S_PORT);
        return false;
    }

    // Clear DMA buffers
    i2s_zero_dma_buffer(I2S_PORT);

    return true;
}

/**
 * Calculate RMS of audio buffer segment
 */
static float calculate_rms(int16_t* samples, size_t count) {
    if (count == 0) return 0.0f;

    int64_t sum_squares = 0;
    for (size_t i = 0; i < count; i++) {
        int32_t sample = samples[i];
        sum_squares += sample * sample;
    }

    float rms = sqrt((float)sum_squares / count);
    // Normalize to 0-1 range (16-bit audio max is 32767)
    return rms / 32768.0f;
}

// ============================================================================
// Public Functions
// ============================================================================

bool audio_init() {
    if (is_initialized) {
        return true;
    }

    Serial.println("Initializing audio capture...");

    // Clear buffer
    memset(audio_buffer, 0, sizeof(audio_buffer));
    write_index = 0;
    read_index = 0;

    // Configure I2S
    if (!configure_i2s()) {
        Serial.println("Failed to configure I2S");
        return false;
    }

    is_initialized = true;
    Serial.println("Audio capture initialized");
    return true;
}

void audio_start() {
    if (!is_initialized || is_running) {
        return;
    }

    Serial.println("Starting audio capture...");
    i2s_start(I2S_PORT);
    is_running = true;
}

void audio_stop() {
    if (!is_running) {
        return;
    }

    Serial.println("Stopping audio capture...");
    i2s_stop(I2S_PORT);
    is_running = false;
}

bool audio_is_running() {
    return is_running;
}

bool audio_get_frame(AudioFrame* frame) {
    if (!frame) return false;

    frame->valid = false;

    // Check if we have enough samples for a frame
    uint32_t available = audio_frames_available();
    if (available < AUDIO_FRAME_SAMPLES) {
        return false;
    }

    // Copy samples to frame
    for (int i = 0; i < AUDIO_FRAME_SAMPLES; i++) {
        frame->samples[i] = audio_buffer[(read_index + i) % AUDIO_BUFFER_SIZE];
    }

    // Update read index
    read_index = (read_index + AUDIO_FRAME_SAMPLES) % AUDIO_BUFFER_SIZE;

    frame->timestamp_ms = millis();
    frame->valid = true;

    return true;
}

float audio_get_level() {
    return current_level;
}

uint32_t audio_frames_available() {
    uint32_t wi = write_index;
    uint32_t ri = read_index;

    if (wi >= ri) {
        return wi - ri;
    } else {
        return AUDIO_BUFFER_SIZE - ri + wi;
    }
}

void audio_process() {
    if (!is_running) {
        return;
    }

    // Temporary buffer for I2S read
    int16_t temp_buffer[DMA_BUF_LEN];
    size_t bytes_read = 0;

    // Read from I2S (non-blocking with short timeout)
    esp_err_t err = i2s_read(I2S_PORT, temp_buffer, sizeof(temp_buffer),
                             &bytes_read, pdMS_TO_TICKS(10));

    if (err != ESP_OK || bytes_read == 0) {
        return;
    }

    size_t samples_read = bytes_read / sizeof(int16_t);

    // Copy to circular buffer
    for (size_t i = 0; i < samples_read; i++) {
        audio_buffer[write_index] = temp_buffer[i];
        write_index = (write_index + 1) % AUDIO_BUFFER_SIZE;

        // Handle buffer overflow (overwrite oldest data)
        if (write_index == read_index) {
            read_index = (read_index + 1) % AUDIO_BUFFER_SIZE;
        }
    }

    // Update level indicator
    current_level = calculate_rms(temp_buffer, samples_read);
}
