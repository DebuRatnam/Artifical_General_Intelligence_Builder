#include <Arduino.h>
#include "dsp_filter.h"

// ── Serial ────────────────────────────────────────────────────────────────────
#define BAUD_RATE       460800

// ── IMU (QMI8658) via I2C ────────────────────────────────────────────────────
#define QMI8658_ADDR    0x6A
#define REG_AZ_L        0x37   // Z-axis accel low byte (verify against datasheet)
#define IMU_SCALE_G     (1.0f / 4096.0f)  // ±8g range, 16-bit

// ── Audio ─────────────────────────────────────────────────────────────────────
#define AUDIO_SAMPLE_RATE  16000
#define AUDIO_BUF_SIZE     512   // MUST be power-of-two

// ── Globals ───────────────────────────────────────────────────────────────────
static float    audio_buf[AUDIO_BUF_SIZE];
static uint16_t audio_idx  = 0;
static uint16_t frame_id   = 0;
static uint32_t last_imu_us = 0;

// ── I2C helper ────────────────────────────────────────────────────────────────
static int16_t qmi8658_read_az(void) {
    Wire.beginTransmission(QMI8658_ADDR);
    Wire.write(REG_AZ_L);
    Wire.endTransmission(false);
    Wire.requestFrom(QMI8658_ADDR, 2);
    if (Wire.available() < 2) return 0;
    uint8_t lo = Wire.read();
    uint8_t hi = Wire.read();
    return (int16_t)((hi << 8) | lo);
}

// ── ADC audio sample (analog pin — swap for PDM if board supports it) ─────────
static float read_audio_sample(void) {
    return (float)(analogRead(A0) - 2048) / 2048.0f;  // 12-bit centre at 2048
}

void setup(void) {
    Serial.begin(BAUD_RATE);
    Wire.begin();
    analogReadResolution(12);
    dsp_filter_init(AUDIO_SAMPLE_RATE, AUDIO_BUF_SIZE);
}

void loop(void) {
    // ── Audio: fill buffer at ~16 kHz via busy sample (no DMA on Arduino core)
    audio_buf[audio_idx++] = read_audio_sample();

    if (audio_idx >= AUDIO_BUF_SIZE) {
        audio_idx = 0;

        // ── IMU: read Z-axis accel
        int16_t raw_az = qmi8658_read_az();
        float   az_g   = raw_az * IMU_SCALE_G;

        // ── DSP: FFT peak frequency
        uint16_t fft_peak_hz = dsp_get_peak_hz(audio_buf, AUDIO_BUF_SIZE);

        // ── Serial TX: timestamp_ms, accel_g, fft_peak_hz, frame_id
        uint32_t ts = millis();
        Serial.print(ts);        Serial.print(',');
        Serial.print(az_g, 4);  Serial.print(',');
        Serial.print(fft_peak_hz); Serial.print(',');
        Serial.println(frame_id);

        frame_id = (frame_id + 1) % 65535;
    }

    // Tight loop — no delay(); audio sampling rate set by loop execution speed
}
