#include "main.h"

BluetoothSerial SerialBT;

// #ifdef VERBOSE
// void DEBUG(const char* msg) {
//     Serial.printf(msg);
//     Serial.printf("\n");
// }
// #else
// void DEBUG(const String& msg) {}
// #endif

void error_led_blink(int times, int delay_ms) {
    for (int i = 0; i < times; i++) {
        digitalWrite(led_pin, HIGH);
        delay(delay_ms);
        digitalWrite(led_pin, LOW);
        delay(delay_ms);
    }
}

void FRESH_SETUP() {
    DEBUG("[+] Setting up device for the first time");
    EEPROM.writeByte(ADDR_PROGRAM_TYPE, PROGRAM_TYPE);
    EEPROM.writeString(ADDR_PIN, "1234\0");
    EEPROM.writeInt(ADDR_CELL_INTERVAL_MS, 100);
    EEPROM.writeFloat(ADDR_CELL_SCALE, 1.0f);
    EEPROM.writeLong(ADDR_CELL_OFFSET, 0);

    EEPROM.commit();
    delay(1000);
    ESP.restart();
}

void COMMS_SETUP() {
    Serial.begin(115200);
    if (!EEPROM.begin(EEPROM_SIZE)) {
        DEBUG("[-] Failed to initialize EEPROM");
        error_led_blink(3, 200);
    } else {
        DEBUG("[+] EEPROM initialized");
    }

    if (EEPROM.readByte(ADDR_PROGRAM_TYPE) != PROGRAM_TYPE) {
        FRESH_SETUP();
    }

    String pin = EEPROM.readString(ADDR_PIN);
    pin.trim();
    if (pin.length() == 0) pin = "1234";
    SerialBT.setPin(pin.c_str());
    if (!SerialBT.begin(PROGRAM_NAME, false)) {
        DEBUG("[-] An error occurred initializing Bluetooth");
        error_led_blink(5, 200);
    } else {
        DEBUG("[+] Bluetooth initialized");
    }
}

void setup() {
    pinMode(led_pin, OUTPUT);
    COMMS_SETUP();
    SENSOR_SETUP_RUN();

    DEBUG("[+] Setup complete");
    DEBUG("===================================");
    DEBUG("[!] Bluetooth INFO");
    DEBUG("[!] SSID: " + String(PROGRAM_NAME));
    DEBUG("[!] PIN: " + String(EEPROM.readString(ADDR_PIN)));
    DEBUG("[!] MAC: " + String(SerialBT.getBtAddressString()));
    DEBUG("===================================");
}

void loop() {
    if (Serial.available()) {
        baca_serial(callback_data_received);
    }
    if (SerialBT.available()) {
        baca_bluetooth(callback_data_received);
    }
    if (cell_reading_queue && xQueuePeek(cell_reading_queue, &cell_reading, 0) != pdTRUE) {
        error_led_blink(10, 50);
    }
    // DEBUG("[+] Reading from loadcell: " + String(cell_reading) + " g");

    vTaskDelay(1 / portTICK_PERIOD_MS);
}