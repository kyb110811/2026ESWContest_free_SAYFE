import serial
import time

PORT = "/dev/ttyACM0"
BAUD = 115200

commands = [
    "nac stop",
    "nac clear",

    "nac preset 48_4_2 0",
    "nac preset 48_4_2 1",

    "nac num_bises 1 0 0",
    "nac num_bises 1 1 0",

    'nac program_info "Construction Safety Chinese" 0 0',
    'nac program_info "Construction Safety Vietnamese" 1 0',

    'nac broadcast_name "CHINESE              " 0',
    'nac broadcast_name "VIETNAMESE           " 1',

    "nac start",
]

print("========================================")
print("Auracast ZH / VI Setup")
print("========================================")

with serial.Serial(PORT, baudrate=BAUD, timeout=1) as ser:
    time.sleep(1)

    for cmd in commands:
        print("SEND:", cmd)
        ser.reset_input_buffer()
        ser.write((cmd + "\r\n").encode("utf-8"))
        ser.flush()
        time.sleep(1)

        response = ser.read_all().decode(
            "utf-8",
            errors="ignore",
        ).strip()

        if response:
            print("RECV:", response)

print("========================================")
print("Auracast setup complete")
print("BIG 0 : ZH")
print("BIG 1 : VI")
print("========================================")
