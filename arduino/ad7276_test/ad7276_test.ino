#include <Arduino.h>

#define AD7276_SCLK  18
#define AD7276_MISO  19
#define AD7276_CS    4

uint16_t readAD7276RawWord() {
  uint16_t rawWord = 0;

  digitalWrite(AD7276_SCLK, HIGH);
  delayMicroseconds(2);
  digitalWrite(AD7276_CS, LOW);
  delayMicroseconds(2);

  for (int bit = 0; bit < 16; bit++) {
    digitalWrite(AD7276_SCLK, LOW);
    delayMicroseconds(2);
    rawWord = (rawWord << 1) | (digitalRead(AD7276_MISO) ? 1 : 0);
    digitalWrite(AD7276_SCLK, HIGH);
    delayMicroseconds(2);
  }

  digitalWrite(AD7276_CS, HIGH);
  return rawWord;
}

uint16_t readAD7276Value() {
  return (readAD7276RawWord() >> 2) & 0x0FFF;
}

void setup() {
  Serial.begin(115200);

  pinMode(AD7276_CS, OUTPUT);
  pinMode(AD7276_SCLK, OUTPUT);
  pinMode(AD7276_MISO, INPUT_PULLUP);

  digitalWrite(AD7276_CS, HIGH);
  digitalWrite(AD7276_SCLK, HIGH);

  delay(1000);
  Serial.println("AD7276 test start");
}

void loop() {
  digitalWrite(AD7276_CS, HIGH);
  digitalWrite(AD7276_SCLK, HIGH);
  delayMicroseconds(100);
  int idleMiso = digitalRead(AD7276_MISO);

  uint16_t rawWord = readAD7276RawWord();
  uint16_t value = (rawWord >> 2) & 0x0FFF;
  float voltage = value * (3.3f / 4095.0f);

  Serial.print("idleMISO=");
  Serial.print(idleMiso);
  Serial.print(" ");
  Serial.print("rawWord=0x");
  if (rawWord < 0x1000) Serial.print("0");
  if (rawWord < 0x0100) Serial.print("0");
  if (rawWord < 0x0010) Serial.print("0");
  Serial.print(rawWord, HEX);
  Serial.print(" value=");
  Serial.print(value);
  Serial.print(" voltage=");
  Serial.println(voltage, 3);

  delay(500);
}
