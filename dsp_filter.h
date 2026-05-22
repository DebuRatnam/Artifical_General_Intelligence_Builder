#pragma once
#include <stdint.h>

void     dsp_filter_init(uint32_t sample_rate, uint16_t buf_size);
uint16_t dsp_get_peak_hz(float *samples, uint16_t n);
