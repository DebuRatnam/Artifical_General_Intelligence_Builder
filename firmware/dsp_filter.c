#include "dsp_filter.h"
#include <Arduino.h>

// ── CMSIS-DSP (linked via arduino-TuyaOpen ARM core) ─────────────────────────
#include "arm_math.h"

#define FFT_SIZE  512   // MUST match AUDIO_BUF_SIZE in main.c; power-of-two only

static arm_rfft_fast_instance_f32 fft_inst;
static float fft_input[FFT_SIZE];
static float fft_output[FFT_SIZE];
static float fft_mag[FFT_SIZE / 2];

static uint32_t _sample_rate = 16000;
static uint16_t _buf_size    = FFT_SIZE;

// ── Hann window coefficients (pre-computed at init) ──────────────────────────
static float hann_win[FFT_SIZE];

// Precompute Hann window coefficients into the static `hann_win` table.
// Called once during init so the per-frame FFT path only multiplies.
static void compute_hann_window(uint16_t n) {
    for (uint16_t i = 0; i < n; i++) {
        hann_win[i] = 0.5f * (1.0f - arm_cos_f32(2.0f * PI * i / (n - 1)));
    }
}

// ── Public API ────────────────────────────────────────────────────────────────
// One-time init. Stores the sample rate (used for bin→Hz conversion),
// initializes the CMSIS-DSP real-FFT instance for FFT_SIZE, and
// precomputes the Hann window. Call once from setup().
void dsp_filter_init(uint32_t sample_rate, uint16_t buf_size) {
    _sample_rate = sample_rate;
    _buf_size    = buf_size;
    arm_rfft_fast_init_f32(&fft_inst, FFT_SIZE);
    compute_hann_window(FFT_SIZE);
}

// Compute the dominant frequency (Hz) of an audio buffer.
// Steps: Hann-window → real FFT → magnitude spectrum → argmax (skip
// the DC bin) → convert bin index to Hz. Returns 0..(sample_rate/2).
uint16_t dsp_get_peak_hz(float *samples, uint16_t n) {
    // Apply Hann window
    for (uint16_t i = 0; i < n; i++) {
        fft_input[i] = samples[i] * hann_win[i];
    }

    // Forward FFT
    arm_rfft_fast_f32(&fft_inst, fft_input, fft_output, 0);

    // Magnitude spectrum (first N/2 bins)
    arm_cmplx_mag_f32(fft_output, fft_mag, FFT_SIZE / 2);

    // Find peak bin (skip DC bin 0)
    float    max_val = 0.0f;
    uint16_t peak_bin = 1;
    for (uint16_t i = 1; i < FFT_SIZE / 2; i++) {
        if (fft_mag[i] > max_val) {
            max_val  = fft_mag[i];
            peak_bin = i;
        }
    }

    // Convert bin index → Hz
    return (uint16_t)((uint32_t)peak_bin * _sample_rate / FFT_SIZE);
}
