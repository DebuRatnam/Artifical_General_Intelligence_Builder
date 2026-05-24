#include <Arduino.h>
#include <Wire.h>
#include "dvpCamera.h"
#include "dsp_filter.h"

#define BAUD_RATE          460800
#define QMI8658_ADDR       0x6A
#define REG_AZ_L           0x37
#define IMU_SCALE_G        (1.0f / 4096.0f)
#define AUDIO_SAMPLE_RATE  16000
#define AUDIO_BUF_SIZE     512
#define CAMERA_PERIOD_MS   500   // ~2 fps to fit 460800 baud

static float    audio_buf[AUDIO_BUF_SIZE];
static uint16_t audio_idx     = 0;
static uint16_t frame_id      = 0;
static uint16_t cam_frame_id  = 0;
static uint32_t last_cam_ms   = 0;
static bool     camera_ok     = false;

Camera camera;

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

static float read_audio_sample(void) {
    return (float)(analogRead(A0) - 2048) / 2048.0f;
}

static void tx_camera_frame(void) {
    if (!camera_ok) return;
    uint32_t now = millis();
    if (now - last_cam_ms < CAMERA_PERIOD_MS) return;
    last_cam_ms = now;

    CameraFrame frame;
    if (OPRT_OK != camera.getFrame(frame, CameraFormat::JPEG, 0)) return;
    if (!frame.isComplete || frame.dataLen == 0) return;

    Serial.print("J,");
    Serial.print(frame.dataLen);
    Serial.print(',');
    Serial.println(cam_frame_id++);
    Serial.write(frame.data, frame.dataLen);
}

void setup(void) {
    Serial.begin(BAUD_RATE);
    Wire.begin();
    dsp_filter_init(AUDIO_SAMPLE_RATE, AUDIO_BUF_SIZE);

    if (OPRT_OK == board_register_hardware()) {
        if (OPRT_OK == camera.begin(CameraResolution::RES_240X240, 10, CameraFormat::JPEG)) {
            camera_ok = true;
        }
    }
}

void loop(void) {
    audio_buf[audio_idx++] = read_audio_sample();

    if (audio_idx >= AUDIO_BUF_SIZE) {
        audio_idx = 0;

        int16_t  raw_az      = qmi8658_read_az();
        float    az_g        = raw_az * IMU_SCALE_G;
        uint16_t fft_peak_hz = dsp_get_peak_hz(audio_buf, AUDIO_BUF_SIZE);
        uint32_t ts          = millis();

        Serial.print("T,");
        Serial.print(ts);          Serial.print(',');
        Serial.print(az_g, 4);     Serial.print(',');
        Serial.print(fft_peak_hz); Serial.print(',');
        Serial.println(frame_id);

        frame_id = (frame_id + 1) % 65535;

        tx_camera_frame();
    }
}
