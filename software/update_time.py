import serial
import datetime

current_utc = datetime.datetime.utcnow()
ser = serial.Serial("/dev/tty.usbmodem2111301", 115200, timeout=1)

timestring = f"{current_utc.year}, {current_utc.month}, {current_utc.day}, 0, {current_utc.hour}, {current_utc.minute}, {current_utc.second}"
print(timestring)
ser.write(bytes(timestring, encoding="utf-8"))
ser.write("\r\n".encode())
print(ser.readlines())

ser.close()
