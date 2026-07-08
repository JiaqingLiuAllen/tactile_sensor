#define CD4067_1_S0  33
#define CD4067_1_S1  25
#define CD4067_1_S2  26
#define CD4067_1_S3  27

#define CD4067_2_S0  21
#define CD4067_2_S1  22
#define CD4067_2_S2  23
#define CD4067_2_S3  14

#define ADC_INPUT 36
#define SAMPLES_PER_CHANNEL 3
#define SCAN_DELAY 0

#define MATRIX_SIZE 7

void setup() {
  Serial.begin(250000);

  pinMode(CD4067_1_S0, OUTPUT);
  pinMode(CD4067_1_S1, OUTPUT);
  pinMode(CD4067_1_S2, OUTPUT);
  pinMode(CD4067_1_S3, OUTPUT);

  pinMode(CD4067_2_S0, OUTPUT);
  pinMode(CD4067_2_S1, OUTPUT);
  pinMode(CD4067_2_S2, OUTPUT);
  pinMode(CD4067_2_S3, OUTPUT);

  Serial.println("Initialization complete, starting channel scan...");
}

// channel: 0-15 (corresponds to C0-C15 on CD4067)
void selectChannel(int s0, int s1, int s2, int s3, int channel) {
  digitalWrite(s0, channel & 0x01);
  digitalWrite(s1, (channel >> 1) & 0x01);
  digitalWrite(s2, (channel >> 2) & 0x01);
  digitalWrite(s3, (channel >> 3) & 0x01);
}

float readAverageADC() {
  float sum = 0;
  for (int i = 0; i < SAMPLES_PER_CHANNEL; i++) {
    sum += analogRead(ADC_INPUT) * (3.3 / 4095.0);
    delayMicroseconds(10);
  }
  return sum / SAMPLES_PER_CHANNEL;
}

void loop() {
  float matrix[MATRIX_SIZE][MATRIX_SIZE];

  // C0–C6 on each MUX
  int row_channels[MATRIX_SIZE]    = {0, 1, 2, 3, 4, 5, 6};
  int column_channels[MATRIX_SIZE] = {0, 1, 2, 3, 4, 5, 6};

  for (int r = 0; r < MATRIX_SIZE; r++) {
    selectChannel(CD4067_2_S0, CD4067_2_S1, CD4067_2_S2, CD4067_2_S3, row_channels[r]);
    delayMicroseconds(100);

    for (int c = 0; c < MATRIX_SIZE; c++) {
      selectChannel(CD4067_1_S0, CD4067_1_S1, CD4067_1_S2, CD4067_1_S3, column_channels[c]);
      delayMicroseconds(100);

      float voltage = readAverageADC();
      matrix[r][c] = voltage;
    }
  }

  Serial.println("Matrix updated:");
  for (int i = 0; i < MATRIX_SIZE; i++) {
    for (int j = 0; j < MATRIX_SIZE; j++) {
      Serial.print(matrix[i][j], 3);
      if (j < MATRIX_SIZE - 1) Serial.print(",");
    }
    Serial.println();
  }

  delay(SCAN_DELAY);
}






// #define CD4067_1_S0  33
// #define CD4067_1_S1  25
// #define CD4067_1_S2  26
// #define CD4067_1_S3  27

// #define CD4067_2_S0  21
// #define CD4067_2_S1  22
// #define CD4067_2_S2  23
// #define CD4067_2_S3  14

// #define ADC_INPUT 36               // ADC1_CH0 on ESP32
// #define SAMPLES_PER_CHANNEL 3     // Take 3 readings per point
// #define SCAN_DELAY 100            // Delay (ms) between matrix scans

// void setup() {
//   Serial.begin(250000);  // High-speed debug output

//   // Initialize all address pins as OUTPUT
//   pinMode(CD4067_1_S0, OUTPUT);
//   pinMode(CD4067_1_S1, OUTPUT);
//   pinMode(CD4067_1_S2, OUTPUT);
//   pinMode(CD4067_1_S3, OUTPUT);

//   pinMode(CD4067_2_S0, OUTPUT);
//   pinMode(CD4067_2_S1, OUTPUT);
//   pinMode(CD4067_2_S2, OUTPUT);
//   pinMode(CD4067_2_S3, OUTPUT);

//   Serial.println("Initialization complete, starting channel scan...");
// }

// void selectChannel(int s0, int s1, int s2, int s3, int channel) {
//   int ch = channel - 1;  // Convert to 0-based index (if input is 1–16)
//   digitalWrite(s0, ch & 0x01);           // Write least significant bit to S0
//   digitalWrite(s1, (ch >> 1) & 0x01);    // Shift right by 1, write to S1
//   digitalWrite(s2, (ch >> 2) & 0x01);    // Shift right by 2, write to S2
//   digitalWrite(s3, (ch >> 3) & 0x01);    // Shift right by 3, write to S3
// }

// float readAverageADC() {
//   float sum = 0;
//   for (int i = 0; i < SAMPLES_PER_CHANNEL; i++) {
//     sum += analogRead(ADC_INPUT) * (3.3 / 4095.0);  // Convert raw ADC to volts
//     delayMicroseconds(10);
//   }
//   return sum / SAMPLES_PER_CHANNEL;
// }

// void loop() {

//   // put your main code here, to run repeatedly:
//   // HERE
//   float matrix[3][3];  // Create a NxN array to store the sensor voltage matrix

//   // HERE
//   for (int ch2 = 1; ch2 <= 3; ch2++) {  // Loop through rows 1 to 4 (MUX2)
//     selectChannel(CD4067_2_S0, CD4067_2_S1, CD4067_2_S2, CD4067_2_S3, ch2);  // Select the current row
//     delayMicroseconds(500);  // Allow signal to settle

//     // HERE
//     int ch1_list[] = {1, 2, 3};  // Define column numbers to scan

//     // HERE
//     for (int i = 0; i < 3; i++) {  // Loop through columns 1 to 4 (MUX1)
//       int ch1 = ch1_list[i];  // Get the column index
//       selectChannel(CD4067_1_S0, CD4067_1_S1, CD4067_1_S2, CD4067_1_S3, ch1);  // Select the current column
//       delayMicroseconds(500);  // Allow signal to settle

//       float voltage = readAverageADC();  // Read average voltage from sensor
//       matrix[i][ch2 - 1] = voltage;  // Store the voltage in matrix at [column][row]
//     }
//   }
//     Serial.println("Matrix updated:");  // Output message

//   // HERE
//   for (int i = 0; i < 3; i++) {  // Loop through rows
//     for (int j = 0; j < 3; j++) {  // Loop through columns
//       Serial.print(matrix[i][j], 3);  // Print voltage with 4 decimal digits
//       if (j < 2) Serial.print(",");  // Print comma except after last element
//     }
//     Serial.println();  // Move to next line after each row
//   }

//   delay(SCAN_DELAY);  // Wait before scanning matrix again
// }

