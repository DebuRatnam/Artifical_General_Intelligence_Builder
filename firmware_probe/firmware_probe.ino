#include <Arduino.h>
#include "dvpCamera.h"
#include "Log.h"

Camera camera;

void setup() {
    Serial.begin(460800);
    Log.begin();
    delay(500);

    Serial.println("=== CAMERA PROBE START ===");

    if (OPRT_OK != board_register_hardware()) {
        Serial.println("FAIL: board_register_hardware");
        return;
    }
    Serial.println("OK: board_register_hardware");

    OPERATE_RET r = camera.begin(CameraResolution::RES_240X240, 10, CameraFormat::JPEG);
    if (OPRT_OK != r) {
        Serial.print("FAIL: camera.begin err=0x");
        Serial.println((uint32_t)r, HEX);
        return;
    }
    Serial.print("OK: camera.begin  W=");
    Serial.print(camera.getWidth());
    Serial.print(" H=");
    Serial.print(camera.getHeight());
    Serial.print(" FPS=");
    Serial.println(camera.getFPS());
}

void loop() {
    CameraFrame frame;
    if (OPRT_OK == camera.getFrame(frame, CameraFormat::JPEG, 500)) {
        Serial.print("FRAME id=");
        Serial.print(frame.id);
        Serial.print(" len=");
        Serial.print(frame.dataLen);
        Serial.print(" complete=");
        Serial.println(frame.isComplete ? 1 : 0);
    } else {
        Serial.println("FRAME timeout");
    }
    delay(500);
}
