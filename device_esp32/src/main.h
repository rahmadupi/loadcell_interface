#pragma once
#include <Arduino.h>
#include <BluetoothSerial.h>
#include <EEPROM.h>

#ifdef BOGDE_HX711
#include <HX711.h>
#else
#include <HX711_ADC.h>
#endif

#include <WiFi.h>
#include <math.h>

#include <mutex>
#include <vector>
#ifdef VERBOSE
#define DEBUG(x) Serial.println(x)
#else
#define DEBUG(x)
#endif

/*
    DEFINISI KONSTANTA
*/
#define EEPROM_SIZE 128
#define PROGRAM_TYPE 0xAB
#define PROGRAM_NAME "ESP32_LOADCELL"

/*
    DEFINISI ENUM
*/
enum MODE {
    SETUP = 0,
    RUN,
    ACTIVE,
    STOP,
    CALIBRATE,
};

enum METHOD {
    SERIAL_COM = 0,
    BLUETOOTH_COM,
};

enum COMMAND {
    PING = 0,
    RESET_DEFAULT,
    GET_PIN,
    GET_MODE,
    GET_SCALE,
    GET_READING,
    SET_PIN,
    SET_MODE,
    SET_TARE,
    SET_SCALE,
};

enum EEPROM_ADDRESS {
    ADDR_PIN = 0,

    ADDR_CELL_SCALE = 16,
    ADDR_CELL_OFFSET = 20,
    ADDR_CELL_INTERVAL_MS = 24,

    ADDR_PROGRAM_TYPE = 120,
};

/*
    DEFINISI PIN
*/
#define led_pin 2
#define CELL_DOUT_PIN 27
#define CELL_SCK_PIN 14

/*
    FUNGSI
*/
// void DEBUG(const char* msg);
/**
 * @brief fungsi untuk melakukan pembacaan data dari serial
 * @param callback fungsi callback yang akan dipanggil saat data diterima
 */
void send_data(const uint8_t* data, int len, METHOD method);

/**
 * @brief fungsi untuk melakukan pembacaan data dari serial
 * @param callback fungsi callback yang akan dipanggil saat data diterima
 */
void baca_bluetooth(void (*callback)(const uint8_t* data, int len, METHOD method));
/**
 * @brief fungsi untuk melakukan pembacaan data dari serial
 * @param callback fungsi callback yang akan dipanggil saat data diterima
 */
void baca_serial(void (*callback)(const uint8_t* data, int len, METHOD method));

/**
 * @brief fungsi untuk menangani hasil pembacaan data dari serial
 * @param data pointer ke data yang diterima
 * @param len panjang data yang diterima
 * @param method metode komunikasi yang digunakan (SERIAL atau BLUETOOTH)
 */
void callback_data_received(const uint8_t* data, int len, METHOD method);

/**
 * @brief fungsi untuk memproses perintah yang diterima
 * @param command perintah yang diterima
 * @param data pointer ke data yang diterima
 * @param len panjang data yang diterima
 * @param index_mac_address index MAC pengirim (sesuai dengan array mac_addresses), default -1 (jika dari serial)
 */
void process_perintah(const uint8_t* data, int len, METHOD method);

/**
 * @brief fungsi untuk buat ngasi tau kalo error
 * @param times jumlah kali LED akan berkedip
 * @param delay_ms durasi delay dalam milidetik antara kedipan LED
 */
void error_led_blink(int times, int delay_ms);

// /**
//  * @brief fungsi untuk buat ngasi tau kalo error
//  */
void FRESH_SETUP();

void COMMS_SETUP();

void SENSOR_SETUP_RUN();
void SENSOR_CALIBRATE(uint8_t step, float known_weight);
void SENSOR_LOOP();

/*
   Variabel dan Konstanta
*/

extern BluetoothSerial SerialBT;
extern std::mutex data_out_mtx;
extern std::mutex data_in_mtx;

#ifdef BOGDE_HX711
extern HX711 cell;
#else
extern HX711_ADC cell;
#endif

extern TaskHandle_t cell_task_handle;
extern MODE loadcell_mode;
extern float cell_reading;
extern uint32_t cell_interval_ms;
extern METHOD comms_method;
extern QueueHandle_t cell_reading_queue;