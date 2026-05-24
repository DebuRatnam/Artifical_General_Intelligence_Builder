#include "dsp_filter.h"
#include <Arduino.h>
#include <arduinoFFT.h>

#define FFT_SIZE 512   // MUST match AUDIO_BUF_SIZE in firmware.ino; power-of-two only

static float fft_real[FFT_SIZE];
static float fft_imag[FFT_SIZE];

static uint32_t _sample_rate = 16000;
static uint16_t _buf_size    = FFT_SIZE;

static ArduinoFFT<float> FFT = ArduinoFFT<float>(fft_real, fft_imag, FFT_SIZE, 16000.0f);

void dsp_filter_init(uint32_t sample_rate, uint16_t buf_size) {
    _sample_rate = sample_rate;
    _buf_size    = buf_size;
    FFT = ArduinoFFT<float>(fft_real, fft_imag, FFT_SIZE, (float)sample_rate);
}

uint16_t dsp_get_peak_hz(float *samples, uint16_t n) {
    for (uint16_t i = 0; i < FFT_SIZE; i++) {
        fft_real[i] = (i < n) ? samples[i] : 0.0f;
        fft_imag[i] = 0.0f;
    }

    FFT.windowing(FFTWindow::Hann, FFTDirection::Forward);
    FFT.compute(FFTDirection::Forward);
    FFT.complexToMagnitude();

    float    max_val  = 0.0f;
    uint16_t peak_bin = 1;
    for (uint16_t i = 1; i < FFT_SIZE / 2; i++) {
        if (fft_real[i] > max_val) {
            max_val  = fft_real[i];
            peak_bin = i;
        }
    }

    return (uint16_t)((uint32_t)peak_bin * _sample_rate / FFT_SIZE);
}
