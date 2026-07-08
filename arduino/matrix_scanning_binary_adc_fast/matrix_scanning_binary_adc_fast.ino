#include <Arduino.h>
#include "soc/gpio_struct.h"

#define CD4067_1_S0  33
#define CD4067_1_S1  25
#define CD4067_1_S2  26
#define CD4067_1_S3  27

#define CD4067_2_S0  21
#define CD4067_2_S1  22
#define CD4067_2_S2  23
#define CD4067_2_S3  14

#define AD7276_SCLK  18
#define AD7276_MISO  19
#define AD7276_CS    4

#define SETTLE_DELAY_US 1
#define SCAN_DELAY 0

#define MATRIX_SIZE 7
#define BAUD_RATE 1500000

const float DIVIDER_RESISTOR_OHMS = 660.0f;
const uint8_t MAGIC[] = {'M', '7', 'X', 'B'};
const uint8_t PROTOCOL_VERSION = 1;
const uint8_t PAYLOAD_TYPE_ADC_U16 = 1;

const size_t VALUE_COUNT = MATRIX_SIZE * MATRIX_SIZE;
const size_t PAYLOAD_BYTES = VALUE_COUNT * sizeof(uint16_t);
const size_t FRAME_BYTES = 4 + 1 + 1 + 1 + 1 + 4 + 4 + PAYLOAD_BYTES + 2;

uint32_t frameIndex = 0;
uint16_t matrixAdc[MATRIX_SIZE][MATRIX_SIZE];

const uint32_t AD7276_SCLK_MASK = 1UL << AD7276_SCLK;
const uint32_t AD7276_MISO_MASK = 1UL << AD7276_MISO;
const uint32_t AD7276_CS_MASK = 1UL << AD7276_CS;

inline void shortAdcDelay() {
  asm volatile(
    "nop\n nop\n nop\n nop\n"
    "nop\n nop\n nop\n nop\n"
    "nop\n nop\n nop\n nop\n"
    "nop\n nop\n nop\n nop\n"
  );
}

void appendByte(uint8_t *buffer, size_t &idx, uint8_t value, uint16_t &checksum) {
  buffer[idx++] = value;
  checksum += value;
}

void appendUint16LE(uint8_t *buffer, size_t &idx, uint16_t value, uint16_t &checksum) {
  appendByte(buffer, idx, value & 0xFF, checksum);
  appendByte(buffer, idx, (value >> 8) & 0xFF, checksum);
}

void appendUint32LE(uint8_t *buffer, size_t &idx, uint32_t value, uint16_t &checksum) {
  appendByte(buffer, idx, value & 0xFF, checksum);
  appendByte(buffer, idx, (value >> 8) & 0xFF, checksum);
  appendByte(buffer, idx, (value >> 16) & 0xFF, checksum);
  appendByte(buffer, idx, (value >> 24) & 0xFF, checksum);
}

void selectChannel(int s0, int s1, int s2, int s3, int channel) {
  digitalWrite(s0, channel & 0x01);
  digitalWrite(s1, (channel >> 1) & 0x01);
  digitalWrite(s2, (channel >> 2) & 0x01);
  digitalWrite(s3, (channel >> 3) & 0x01);
}

uint16_t readAD7276() {
  uint16_t rawWord = 0;

  GPIO.out_w1tc = AD7276_CS_MASK;
  shortAdcDelay();

  for (int bit = 0; bit < 16; bit++) {
    GPIO.out_w1ts = AD7276_SCLK_MASK;
    shortAdcDelay();
    rawWord = (rawWord << 1) | ((GPIO.in & AD7276_MISO_MASK) ? 1 : 0);
    GPIO.out_w1tc = AD7276_SCLK_MASK;
    shortAdcDelay();
  }

  GPIO.out_w1ts = AD7276_CS_MASK;

  return (rawWord >> 2) & 0x0FFF;
}

void scanMatrix() {
  const int rowChannels[MATRIX_SIZE] = {0, 1, 2, 3, 4, 5, 6};
  const int columnChannels[MATRIX_SIZE] = {0, 1, 2, 3, 4, 5, 6};

  for (int r = 0; r < MATRIX_SIZE; r++) {
    selectChannel(CD4067_2_S0, CD4067_2_S1, CD4067_2_S2, CD4067_2_S3, rowChannels[r]);
    delayMicroseconds(SETTLE_DELAY_US);

    for (int c = 0; c < MATRIX_SIZE; c++) {
      selectChannel(CD4067_1_S0, CD4067_1_S1, CD4067_1_S2, CD4067_1_S3, columnChannels[c]);
      delayMicroseconds(SETTLE_DELAY_US);

      matrixAdc[r][c] = readAD7276();
    }
  }
}

void writeBinaryFrame() {
  uint8_t frame[FRAME_BYTES];
  size_t idx = 0;
  uint16_t checksum = 0;

  for (size_t i = 0; i < sizeof(MAGIC); i++) {
    frame[idx++] = MAGIC[i];
  }

  appendByte(frame, idx, PROTOCOL_VERSION, checksum);
  appendByte(frame, idx, MATRIX_SIZE, checksum);
  appendByte(frame, idx, MATRIX_SIZE, checksum);
  appendByte(frame, idx, PAYLOAD_TYPE_ADC_U16, checksum);
  appendUint32LE(frame, idx, frameIndex, checksum);
  appendUint32LE(frame, idx, millis(), checksum);

  for (int r = 0; r < MATRIX_SIZE; r++) {
    for (int c = 0; c < MATRIX_SIZE; c++) {
      appendUint16LE(frame, idx, matrixAdc[r][c], checksum);
    }
  }

  frame[idx++] = checksum & 0xFF;
  frame[idx++] = (checksum >> 8) & 0xFF;

  Serial.write(frame, idx);
}

void setup() {
  Serial.begin(BAUD_RATE);

  pinMode(CD4067_1_S0, OUTPUT);
  pinMode(CD4067_1_S1, OUTPUT);
  pinMode(CD4067_1_S2, OUTPUT);
  pinMode(CD4067_1_S3, OUTPUT);

  pinMode(CD4067_2_S0, OUTPUT);
  pinMode(CD4067_2_S1, OUTPUT);
  pinMode(CD4067_2_S2, OUTPUT);
  pinMode(CD4067_2_S3, OUTPUT);

  pinMode(AD7276_CS, OUTPUT);
  pinMode(AD7276_SCLK, OUTPUT);
  pinMode(AD7276_MISO, INPUT);
  digitalWrite(AD7276_CS, HIGH);
  digitalWrite(AD7276_SCLK, LOW);

  delay(1000);
  readAD7276();
}

void loop() {
  scanMatrix();
  writeBinaryFrame();
  frameIndex++;
  delay(SCAN_DELAY);
}
