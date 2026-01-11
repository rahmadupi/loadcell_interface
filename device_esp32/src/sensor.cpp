

#include "main.h"

#ifdef BOGDE_HX711
HX711 cell;
#else
HX711_ADC cell(CELL_DOUT_PIN, CELL_SCK_PIN);
#endif

TaskHandle_t cell_task_handle;
QueueHandle_t cell_reading_queue;

float cell_reading = 0.0;
uint32_t cell_interval_ms = 100;
MODE loadcell_mode = MODE::RUN;
METHOD comms_method = METHOD::SERIAL_COM;

void SENSOR_CALIBRATE(uint8_t step, float known_weight) {
    static float known_weight_static;
    if (step == 0) {
        known_weight_static = known_weight;
        DEBUG("[+] Begining calibration...");
        delay(250);
        DEBUG("[+] Begining calibration..");
        delay(250);
        DEBUG("[+] Begining calibration.");
        delay(250);
        DEBUG("[+] Remove any weight from the scale.");
    } else if (step == 1) {
        DEBUG("[+] Tare and zeroing scale...");
#ifdef BOGDE_HX711
        // Lawas
        cell.set_scale();
        delay(100);
        cell.tare();
#else
        cell.tareNoDelay();
        if (cell.getTareStatus())
            DEBUG("[+] Tare complete");
#endif

    } else if (step == 2) {
        DEBUG("[+] Place a known weight on the scale.");
    } else if (step == 3) {
        DEBUG("[+] Reading value...");

#ifdef BOGDE_HX711
        // Lawas
        // read raw value (offset already applied) averaged for stability
        long raw = cell.get_value(10);  // raw = read_average - offset
        // long raw = cell.get_units(10);
        if (known_weight_static <= 0.0f) {
            DEBUG("[-] Invalid known weight");
            return;
        }
        float scale_factor = (float)raw / known_weight_static;
        cell.set_scale(scale_factor);
        Serial.printf("[+] Calibration complete. Scale factor: %.5f\n", scale_factor);
        DEBUG("[+] Reading after calibration: " + String(cell.get_units(10)) + " g");
        EEPROM.writeLong(ADDR_CELL_OFFSET, cell.get_offset());
#else
        cell.refreshDataSet();
        float scale_factor = cell.getNewCalibration(known_weight_static);
        Serial.printf("[+] Calibration complete. Scale factor: %.5f\n", scale_factor);
        DEBUG("[+] Reading after calibration: " + String(cell.getData()) + " g");
#endif

        // Save to EEPROM
        EEPROM.writeFloat(ADDR_CELL_SCALE, scale_factor);
        EEPROM.commit();
        DEBUG("[+] Calibration data saved to EEPROM.");
    }
}

void SENSOR_LOOP(void* pvParameters) {
    // HX711 Loop
    float reading = 0.0;

    TickType_t last_wake = xTaskGetTickCount();
    byte data_sent[5] = {GET_READING};

    while (true) {
        // Lawas
#ifdef BOGDE_HX711
        reading = cell.get_units(1);
        if (!reading)
            reading = 0.0f;
#else
        if (cell.update())
            reading = cell.getData();
        if (!reading)
            reading = 0.0f;
#endif
        if (!isfinite(reading) || isnan(reading)) {
            DEBUG("[!] Invalid loadcell reading (NaN/Inf) detected; substituting 50.0 g");
            reading = 15.0f;
        }

        // #ifdef VERBOSE
        //         DEBUG("[+] Loadcell reading: " + String(reading) + " g");
        // #endif

        if (cell_reading_queue)
            xQueueOverwrite(cell_reading_queue, &reading);

        if (loadcell_mode == MODE::ACTIVE) {
            memcpy(&data_sent[1], &reading, sizeof(float));
            send_data(data_sent, 5, comms_method);
        }

        TickType_t period = pdMS_TO_TICKS((uint32_t)cell_interval_ms);
        if (period == 0) period = 1;
        vTaskDelayUntil(&last_wake, period);
    }
}

void SENSOR_SETUP_RUN() {
    // DEBUG("[+] Initializing Loadcell...");

#ifdef BOGDE_HX711
    // HX711 Setup
    DEBUG("[!] Using Bogde HX711 Library");
    cell.begin(CELL_DOUT_PIN, CELL_SCK_PIN);
    float stored_scale = EEPROM.readFloat(ADDR_CELL_SCALE);
    if (!isfinite(stored_scale) || fabs(stored_scale) < 1e-6f) {
        DEBUG("[!] EEPROM scale invalid or zero; using default scale=1.0 and saving to EEPROM");
        stored_scale = 1.0f;
        EEPROM.writeFloat(ADDR_CELL_SCALE, stored_scale);
        EEPROM.commit();
    }
    cell.set_scale(stored_scale);
    cell.set_offset(EEPROM.readLong(ADDR_CELL_OFFSET));
#else
    // HX711_ADC Setup
    DEBUG("[!] Using olkal HX711_ADC Library");
    cell.begin();
    cell.start(2000, true);
    while (cell.getTareTimeoutFlag() || cell.getSignalTimeoutFlag()) {
        DEBUG("[-] Timeout, check MCU>HX711 wiring and pin designations");
        error_led_blink(1, 100);
    }
    while (!cell.update()) {
        DEBUG("[+] Waiting for Loadcell to stabilize...");
    }

    float stored_scale = EEPROM.readFloat(ADDR_CELL_SCALE);
    if (!isfinite(stored_scale) || fabs(stored_scale) < 1e-6f) {
        DEBUG("[!] EEPROM scale invalid or zero; using default scale=1.0 and saving to EEPROM");
        stored_scale = 1.0f;
        EEPROM.writeFloat(ADDR_CELL_SCALE, stored_scale);
        EEPROM.commit();
    }
    cell.setCalFactor(stored_scale);

#endif

    cell_interval_ms = EEPROM.readInt(ADDR_CELL_INTERVAL_MS);

    if (!cell_reading_queue)
        cell_reading_queue = xQueueCreate(1, sizeof(float));

    if (cell_task_handle == NULL) {
        xTaskCreate(SENSOR_LOOP, "SENSOR", 4096, NULL, 1, &cell_task_handle);
        loadcell_mode = MODE::RUN;
    }
}