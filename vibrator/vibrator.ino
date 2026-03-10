 /*
 * vibrator
 *
 * Arduino code used for vibrating the string or straw for tension measurements.
 *
 * created by Vadim Rusu (vrusu@fnal.gov)
 * edited 09 February 2016
 * by Lauren Yates (yatesla@fnal.gov)
 */

#include <Wire.h>
#include <stdint.h>
#define I2C_ADDRESS 0x27


const int enable = 8;
const int enabledigi = 9;

const int convst = 10;
const int busy = 5;
const int sdata = 4;
const int sclk = 11;
const int dbgPin = 23;

const int baudRate = 115200;
const int dataLength = 400;
const int delaymicro = 120;

void setup()
{
  REG_ADC_MR = (REG_ADC_MR & 0xFFF0F0FF) | 0x000F0300;
  analogReadResolution(12);
  Serial.begin(baudRate); // start serial for output
  Wire.begin();

  pinMode(enable, OUTPUT);
  pinMode(enabledigi, OUTPUT);
  pinMode(convst, OUTPUT);
  pinMode(busy, INPUT);
  pinMode(sdata, INPUT);
  pinMode(sclk, OUTPUT);
  pinMode(dbgPin,OUTPUT);
  digitalWrite(enabledigi, HIGH);
  digitalWrite(enable,LOW);
  digitalWrite(convst,HIGH);
  digitalWrite(sclk,LOW);
}


void startDrive(){
  digitalWrite(enable,HIGH);
}

void endDrive(){
  digitalWrite(enable,LOW);
}

void endDigitize(){
  digitalWrite(enabledigi,LOW);
}

void startDigitize(){
  digitalWrite(enabledigi,HIGH);
}

unsigned int readADC()
{
  unsigned int adcval = 0;
  digitalWrite(convst, LOW);
  delayMicroseconds(1);
  digitalWrite(convst, HIGH);
  delayMicroseconds(5);

  for(int i=16; i--; )
    {
      digitalWrite(sclk,HIGH);
      unsigned int d = digitalRead(sdata);
      digitalWrite(sclk,LOW);
      adcval |= (d<<i);
    }

  delayMicroseconds(1);
  return adcval;
}

void loop()
{
  int v=analogRead(sdata); // what is this for???

  int incomingByte = 0;
  unsigned int adcreadings[dataLength];

  char buffer[8];
  memset(buffer, 0, 8); // Reset the value of the buffer to zero

  unsigned int adcval;


  while (!Serial.available());

  Serial.setTimeout(1000000);

  // Read in the incoming trigger
  Serial.readBytesUntil('\n',buffer,8);
  int incoming = atoi(buffer);

  // Read in the pulse width
  Serial.readBytesUntil('\n',buffer,8);
  int pulse_width = atoi(buffer);

  if (incoming == 5){
    Serial.print("Using a pulse of width (in microseconds): ");
    Serial.println(pulse_width);

    // Pulse the straw
    startDrive();
    delayMicroseconds(pulse_width);
    endDrive();

    delay(3); // Delay between pulse and gate
    startDigitize();

    unsigned int *pReading = adcreadings;
    int iread = 0;
    digitalWrite(dbgPin,HIGH);
    unsigned long tstart = micros();
    do{
      delayMicroseconds(delaymicro);
      *pReading = readADC();
      iread++;
      pReading++;
    } while(iread < dataLength);
    unsigned long elapsed = micros() - tstart;
    endDigitize();
    digitalWrite(dbgPin,LOW);

    // Now send to serial
    for (int i = 0 ; i < dataLength; i++){
      Serial.println(adcreadings[i]);
    }
    // send the elapsed time
    Serial.println(elapsed);
  }

}
