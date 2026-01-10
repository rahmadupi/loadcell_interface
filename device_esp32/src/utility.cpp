#include "main.h"

std::mutex data_out_mtx;
std::mutex data_in_mtx;

void ledStatus(bool active_high) {
    static int led_update_time = 0;
    if ((millis() - led_update_time) > 1000) {
        digitalWrite(led_pin, active_high ? 1 : 0);
        led_update_time = millis();
    } else {
        digitalWrite(led_pin, active_high ? 0 : 1);
    }
}

const char* command_to_string(COMMAND cmd) {
    switch (cmd) {
        case COMMAND::PING:
            return "GET_PING";
        case COMMAND::RESET_DEFAULT:
            return "RESET_DEFAULT";
        case COMMAND::GET_MODE:
            return "GET_MODE";
        case COMMAND::GET_READING:
            return "GET_READING";
        case COMMAND::SET_PIN:
            return "SET_PIN";
        case COMMAND::SET_MODE:
            return "SET_MODE";
        case COMMAND::SET_TARE:
            return "SET_TARE";
        default:
            return "UNKNOWN_COMMAND";
    }
}

void send_data(const uint8_t* data, int len, METHOD method) {
    std::lock_guard<std::mutex> lck(data_out_mtx);

    std::vector<uint8_t> buf;
    buf.reserve(len + 3);
    buf.push_back(0xFD);
    buf.push_back(0x00);
    buf.push_back((uint8_t)len);
    buf.insert(buf.end(), data, data + len);

    // debug
    // DEBUG("[+] Sending data via" + String((method == METHOD::SERIAL_COM ? " SERIAL" : " BLUETOOTH")));
    // for (int i = 0; i < buf.size(); i++) {
    //     Serial.printf("%02X ", buf[i]);
    // }
    // DEBUG();

    if (method == METHOD::SERIAL_COM) {
        Serial.write(buf.data(), buf.size());
        Serial.flush();
    } else if (method == METHOD::BLUETOOTH_COM) {
        SerialBT.write(buf.data(), buf.size());
        SerialBT.flush();
    }
}

void callback_data_received(const uint8_t* data, int len, METHOD method) {
    std::lock_guard<std::mutex> lck(data_in_mtx);
    ledStatus(true);
    DEBUG("[+] Data received via" + String((method == METHOD::SERIAL_COM ? " SERIAL" : " BLUETOOTH")));
    process_perintah(data, len, method);
}

void baca_bluetooth(void (*callback)(const uint8_t* data, int len, METHOD method)) {
    if (SerialBT.read() != 0xFD) return;
    if (SerialBT.read() != 0x00) return;

    int len = SerialBT.read();
    uint8_t data[len];
    SerialBT.readBytes(data, len);
    callback(data, len, METHOD::BLUETOOTH_COM);
}

void baca_serial(void (*callback)(const uint8_t* data, int len, METHOD method)) {
    if (Serial.read() != 0xFD) return;
    if (Serial.read() != 0x00) return;

    int len = Serial.read();
    uint8_t data[len];
    Serial.readBytes(data, len);
    callback(data, len, METHOD::SERIAL_COM);
}

void process_perintah(const uint8_t* data, int len, METHOD method) {
    COMMAND cmd = static_cast<COMMAND>(data[0]);
    DEBUG("[+] Processing command: " + String((int)cmd));

    if (cmd == COMMAND::PING) {
        byte data_sent[2] = {PING, 0};
        comms_method = method;
        method == METHOD::SERIAL_COM ? send_data(data_sent, 2, METHOD::SERIAL_COM) : send_data(data_sent, 2, METHOD::BLUETOOTH_COM);
    }
    if (cmd == COMMAND::RESET_DEFAULT) {
        FRESH_SETUP();
    }
    if (cmd == COMMAND::GET_MODE) {
        byte data_sent[2] = {GET_MODE, (byte)loadcell_mode};
        method == METHOD::SERIAL_COM ? send_data(data_sent, 2, METHOD::SERIAL_COM) : send_data(data_sent, 2, METHOD::BLUETOOTH_COM);
    }
    if (cmd == COMMAND::SET_PIN) {
        String new_pin = "";
        for (int i = 1; i < len; i++) {
            new_pin += (char)data[i];
        }
        new_pin.trim();
        if (new_pin.length() > 0 && new_pin.length() < 4) {
            EEPROM.writeString(ADDR_PIN, new_pin.c_str());
            EEPROM.commit();
            DEBUG("[+] PIN updated to: " + new_pin);
        }
    }
    if (cmd == COMMAND::SET_MODE) {
        MODE new_mode = static_cast<MODE>(data[1]);
        MODE past_mode = loadcell_mode;
        int interval_ms;
        memcpy(&interval_ms, data + 2, sizeof(int));
        loadcell_mode = new_mode;
        DEBUG("[+] Loadcell mode changed to: " + String((int)new_mode));
        if (new_mode == MODE::RUN) {
            if (eTaskGetState(cell_task_handle) == eSuspended)
                vTaskResume(cell_task_handle);
            if (past_mode == new_mode) {
                cell_interval_ms = interval_ms;
            }
        }

        if (new_mode == MODE::ACTIVE) {
            if (eTaskGetState(cell_task_handle) == eSuspended)
                vTaskResume(cell_task_handle);
            if (past_mode == new_mode) {
                cell_interval_ms = interval_ms;
            }
        }

        if (new_mode == MODE::STOP) {
            if (eTaskGetState(cell_task_handle) != eSuspended)
                vTaskSuspend(cell_task_handle);
        }
        if (new_mode == MODE::CALIBRATE) {
            if (eTaskGetState(cell_task_handle) != eSuspended)
                vTaskSuspend(cell_task_handle);
            uint8_t step = data[2];
            uint8_t known_weight = 0;
            if (len >= 4) {
                memcpy(&known_weight, data + 3, sizeof(float));
            }
            if (step <= 3)
                SENSOR_CALIBRATE(step, known_weight);
            if (step == 3)
                if (eTaskGetState(cell_task_handle) == eSuspended)
                    vTaskResume(cell_task_handle);
        }
    }
    if (cmd == COMMAND::SET_TARE) {
        cell.tare();
        DEBUG("[+] Loadcell tared.");
    }
    if (cmd == COMMAND::GET_READING) {
        byte data_sent[5] = {GET_READING};
        memcpy(&data_sent[1], &cell_reading, sizeof(float));
        method == METHOD::SERIAL_COM ? send_data(data_sent, 5, METHOD::SERIAL_COM) : send_data(data_sent, 5, METHOD::BLUETOOTH_COM);
    }
    if (cmd == COMMAND::SET_SCALE) {
        float scale_factor;
        memcpy(&scale_factor, data + 1, sizeof(float));
        cell.set_scale(scale_factor);
        DEBUG("[+] Loadcell scale factor set to: " + String(scale_factor));

        // Save to EEPROM
        EEPROM.writeFloat(ADDR_CELL_SCALE, scale_factor);
        EEPROM.commit();
        Serial.printf("[+] Scale factor saved to EEPROM: %.5f\n", scale_factor);
        Serial.printf("[+] Offset saved to EEPROM: %ld\n", cell.get_offset());
        Serial.printf("[+] Scale reading: %.2f g\n", EEPROM.readFloat(ADDR_CELL_SCALE));
        DEBUG("[+] Scale factor saved to EEPROM.");
    }
}