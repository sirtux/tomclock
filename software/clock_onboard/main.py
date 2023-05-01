import ws2812b
import time
import machine
from ds1307 import DS1307
import _thread

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

# Set up the ws2812 PIO engines
ring = ws2812b.ws2812b(60, 0, 0)
digits = ws2812b.ws2812b(68, 1, 1)

# Color definition

color_r = 5
color_g = 5
color_b = 5

ring_color_r = 2
ring_color_g = 0
ring_color_b = 0

# Init the external RTC Module and stuff
i2c_bus_rtc = machine.I2C(1, scl=machine.Pin(19), sda=machine.Pin(18))
i2c_rtc = DS1307(i2c_bus_rtc)

# Init the internal RTC
rtc = machine.RTC()

# key is year, value 1 is summertime day in march, value 2 is wintertime day in october
switchover_dates = {
    2023: (26, 29),
    2024: (31, 27),
    2025: (30, 26),
    2026: (29, 25),
    2027: (28, 31),
    2028: (26, 29),
    2029: (25, 28),
    2030: (31, 27),
}

wintertime_offset = 1
summertime_offset = 2


def copy_rtc_to_internal_rtc_with_tz():
    print("RTC Sync initiated")
    current_datetime = i2c_rtc.datetime()
    UTC_OFFSET = wintertime_offset
    # All is ugly, as we don't have TZ Info in micropython.
    # We do not care about the exact time, but only the date - so we will have the
    # TZ flipover at 01:00 clock (This is the time we reload the data)

    # Case 1: We are in May to Sept:
    if current_datetime[1] >= 5 and current_datetime[1] <= 9:
        UTC_OFFSET = summertime_offset
    # Case 2: We are in April and on the switch_over date or later:
    if (
        current_datetime[1] == 4
        and current_datetime[2] >= switchover_dates[current_datetime[0]][0]
    ):
        UTC_OFFSET = summertime_offset
    # Case 3: We are in October, but before switchover_date
    if (
        current_datetime[1] == 10
        and current_datetime[2] < switchover_dates[current_datetime[0]][1]
    ):
        UTC_OFFSET = summertime_offset

    # We don't know how long this took, so let's get the RTC time again
    current_datetime = list(i2c_rtc.datetime())
    current_datetime[4] = current_datetime[4] + UTC_OFFSET

    # And now - the great fun: The I2C RTC has a weekday thingy, the internal RTC not. But we have a microsends thingy, which the I2C RTC does not have, joy!
    print()
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
    print(tuple_for_onboard_rtc)

    rtc.datetime(tuple_for_onboard_rtc)


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


def run():
    rtc_available = True
    while True:
        # Every minute we sync the I2C RTC to the internal one
        # Why, you ask? Well, an old swiss watch is more accurate than that thing
        # somebody called RTC.
        
        if rtc.datetime()[6] == 0 and rtc.datetime()[5] == 2 and rtc_available:
            rtc_available = False
            copy_rtc_to_internal_rtc_with_tz()
         
        if rtc.datetime()[6] == 10:
            rtc_available = True
            
        if (
            rtc.datetime()[6] > 14
            and rtc.datetime()[6] < 30
            or rtc.datetime()[6] > 45
            and rtc.datetime()[6] < 59
        ):
            render_and_display_time(
                digits,
                rtc.datetime()[4],
                rtc.datetime()[5],
                rtc.datetime()[6],
                color_r,
                color_g,
                color_b,
            )
        else:
            render_and_display_date(
                digits, rtc.datetime()[2], rtc.datetime()[1], color_r, color_g, color_b
            )
        render_and_display_seconds_ring(
            ring, rtc.datetime()[6], color_r, color_g, color_b
        )
        time.sleep(0.1)


def get_new_time():
    print(
        'To set the clock, run TZ=UTC date +"%Y, %m, %d, 0, %H, %M, %S" > /dev/$yourserialport\n'
    )
    timeinput = input().split(",")
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
    current_datetime = i2c_rtc.datetime()
    print(
        f"New UTC Date: {current_datetime[0]}-{current_datetime[1]}-{current_datetime[2]} {current_datetime[4]}:{current_datetime[5]}:{current_datetime[6]}"
    )

    copy_rtc_to_internal_rtc_with_tz()


if __name__ == "__main__":
    _thread.start_new_thread(run, ())
    while True:
        try:
            get_new_time()
        except ValueError as e:
            print("Got wrong time format, try again")
            print(e)
