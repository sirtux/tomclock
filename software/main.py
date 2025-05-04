import ws2812b
import time
import machine
from ds1307 import DS1307
import posix_tz

# LED Mapping
digit_to_led = {
    "1": [11, 12, 14, 15],
    "2": [0, 10, 11, 12, 3, 13, 4, 5, 6, 16],
    "3": [0, 10, 11, 12, 3, 13, 14, 15, 6, 16],
    "4": [1, 2, 3, 13, 11, 12, 14, 15],
    "5": [0, 10, 1, 2, 3, 13, 14, 15, 6, 16],
    "6": [0, 10, 1, 2, 3, 13, 4, 5, 6, 16, 14, 15],
    "7": [0, 10, 11, 12, 14, 15],
    "8": [0, 10, 1, 2, 11, 12, 3, 13, 4, 5, 14, 15, 6, 16],
    "9": [0, 10, 1, 2, 11, 12, 3, 13, 14, 15, 6, 16],
    "0": [0, 10, 1, 2, 11, 12, 4, 5, 14, 15, 6, 16],
    "dot": [9],
    "colon": [7, 8],
}

# Time Zone
posix_tz.set_tz('CEST-1CET,M3.2.0/2:00:00,M11.1.0/2:00:00')

# Set up the ws2812 PIO engines
ring = ws2812b.ws2812b(60, 0, 0)
digits = ws2812b.ws2812b(68, 1, 1)

# Color definition

color_r = 0
color_g = 10
color_b = 0

ring_color_r = 10
ring_color_g = 0
ring_color_b = 0

# Init the external RTC Module and stuff
i2c_bus_rtc = machine.SoftI2C(scl=machine.Pin(18), sda=machine.Pin(19), freq=4000)
i2c_rtc = DS1307(i2c_bus_rtc)

# Init the internal RTC
rtc = machine.RTC()

def copy_rtc_to_internal_rtc_with_tz():
    print("RTC Sync initiated")
    current_datetime = i2c_rtc.datetime()

    tuple_for_onboard_rtc = (
        current_datetime[0],
        current_datetime[1],
        current_datetime[2],
        current_datetime[3],
        current_datetime[4],
        current_datetime[5],
        current_datetime[6],
        0,
    )
    rtc.datetime(tuple_for_onboard_rtc)
    posix_tz.set_tz('CEST-1CET,M3.2.0/2:00:00,M11.1.0/2:00:00')
    local_datetime = posix_tz.localtime()
    print(posix_tz.localtime())
    print(f"New UTC Date: {local_datetime[0]}-{local_datetime[1]}-{local_datetime[2]} {local_datetime[3]}:{local_datetime[4]}:{local_datetime[5]}")

def render_single_digit(digits, digit, offset, colon, dot, color_r, color_g, color_b):
    for led in digit_to_led[digit]:
        digits.set_pixel(led + offset * 17, color_r, color_g, color_b)
        if colon:
            for led in digit_to_led["colon"]:
                digits.set_pixel(led + offset * 17, color_r, color_g, color_b)
        if dot:
            for led in digit_to_led["dot"]:
                digits.set_pixel(led + offset * 17, color_r, color_g, color_b)


def render_and_display_time(digits, hour, minutes, seconds, color_r, color_g, color_b):
    # Clear the digit buffer
    digits.fill(0, 0, 0)

    # We want the colon only blink every second second
    display_colon = False
    if seconds % 2 == 0:
        display_colon = True

    # We need always 2 digits per field, and to have them easily accesible we use strings
    hour_string = f"{hour:02d}"
    minute_string = f"{minutes:02d}"

    render_single_digit(
        digits, hour_string[0], 0, False, False, color_r, color_g, color_b
    )
    render_single_digit(
        digits, hour_string[1], 1, display_colon, False, color_r, color_g, color_b
    )
    render_single_digit(
        digits, minute_string[0], 2, False, False, color_r, color_g, color_b
    )
    render_single_digit(
        digits, minute_string[1], 3, False, False, color_r, color_g, color_b
    )

    # Show the digits
    digits.show()


def render_and_display_date(digits, day, month, color_r, color_g, color_b):
    # Clear the digit buffer
    digits.fill(0, 0, 0)

    # We need always 2 digits per field, and to have them easily accesible we use strings
    day_string = f"{day:02d}"
    month_string = f"{month:02d}"

    render_single_digit(
        digits, day_string[0], 0, False, False, color_r, color_g, color_b
    )
    render_single_digit(
        digits, day_string[1], 1, False, True, color_r, color_g, color_b
    )
    render_single_digit(
        digits, month_string[0], 2, False, False, color_r, color_g, color_b
    )
    render_single_digit(
        digits, month_string[1], 3, False, True, color_r, color_g, color_b
    )

    # Show the digits
    digits.show()


def render_and_display_seconds_ring(ring, seconds, color_r, color_g, color_b):
    # Clear the digit buffer
    ring.fill(ring_color_r, ring_color_g, ring_color_b)
    ring.set_pixel(seconds, color_r, color_g, color_b)

    # Show the digits
    ring.show()


def render(_):
    local_datetime = posix_tz.localtime()
    try:
        # At every hour at minute 0, we resync the external RTC to the internal RTC
        if local_datetime[4] == 0:
            try:
                copy_rtc_to_internal_rtc_with_tz()
            except:
                machine.reset()

        # We want to display the time for 15s, then 5s with the date
        if (
            # Block 0: 0s up to 15s
            0 <= local_datetime[5] <= 15 or
            # Block 1: 21s to 35s
            21 <= local_datetime[5] <= 35 or
            # Block 2: 40s to 55s
            40 <= local_datetime[5] <= 55
        ):
            render_and_display_time(
                digits,
                local_datetime[3],
                local_datetime[4],
                local_datetime[5],
                color_r,
                color_g,
                color_b,
            )
        else:
            render_and_display_date(
                digits, local_datetime[2], local_datetime[1], color_r, color_g, color_b
            )
        render_and_display_seconds_ring(
            ring, rtc.datetime()[6], color_r, color_g, color_b
        )
        time.sleep(0.1)
    except:
        machine.reset()


def get_new_time():
    print(
        'To set the clock, run TZ=UTC date +"%Y, %m, %d, 0, %H, %M, %S" > /dev/$yourserialport\n'
    )
    timeinput = input().split(",")

    if timeinput[0] == "x":
        raise Exception()

    timetuple = tuple(
        [
            int(timeinput[0]),
            int(timeinput[1]),
            int(timeinput[2]),
            int(timeinput[3]),
            int(timeinput[4]),
            int(timeinput[5]),
            int(timeinput[6]),
        ]
    )
    current_datetime = i2c_rtc.datetime()
    print(
        f"Current UTC Date: {current_datetime[0]}-{current_datetime[1]}-{current_datetime[2]} {current_datetime[4]}:{current_datetime[5]}:{current_datetime[6]}"
    )
    i2c_rtc.datetime(datetime=timetuple)
    print(f"Received tuple: {timetuple}")
    current_datetime = i2c_rtc.datetime()
    print(
        f"New UTC Date: {current_datetime[0]}-{current_datetime[1]}-{current_datetime[2]} {current_datetime[4]}:{current_datetime[5]}:{current_datetime[6]}"
    )

    copy_rtc_to_internal_rtc_with_tz()


if __name__ == "__main__":

    try:
        copy_rtc_to_internal_rtc_with_tz()
    except:
        machine.reset()
    timer1 = machine.Timer()
    timer1.init(period=100, callback=render)
    while True:
        try:
            get_new_time()
        except ValueError as e:
            print("Got wrong time format, try again")
            print(e)

