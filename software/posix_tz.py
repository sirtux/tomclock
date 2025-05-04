# https://github.com/clach04/py-posix_tz
# NOTE short names for space reasons
"""
time.time() is int on esp32 Micropython, float in CPython
time.localtime() is tuple in Micropython, struct/class/namedtuple in CPython (3.x) with different attributes
"""

from collections import namedtuple
import re
import time


global_tzd = None  # or UTC

m_tuple = namedtuple('m', ('month', 'occur', 'day', 'hour', 'min', 'sec'))
def parse_mstr(s):
    if s[0] != 'M':
        raise NotImplemented('non-M %s not supported' % s[0])  # e.g. Julian
    ss = s.split('/')
    m = ss[0]
    if len(ss) == 2:
        t = ss[1]
    else:
        t = '2:00:00'
    month, occur, day = map(int, m[1:].split('.'))  # TODO catch non-int errors
    h, min, sec = map(int, t.split(':'))  # TODO catch non-int errors
    return m_tuple(month, occur, day, h, min, sec)

name_offset_re = re.compile(r"^([A-Z]+)([+-]?)(\d+)(?::(\d+))?(?::(\d+))?")  # TODO revisit this
# timezone details tuple
tzd_tuple = namedtuple('tzd', ('name', 'offset', 'dst_name', 'start', 'end', 'dst_offset'))  # offsets are seconds
def parse_tz(s):
    #import pdb; pdb.set_trace()
    ss = s.split(',')
    if len(ss) == 1:
        # no DST
        #import pdb; pdb.set_trace()
        x = re.match(name_offset_re, s)
        if x:
            #tzname, sign, d_hour, d_min, d_sec = re.match(name_offset_re, s).groups(default=0)  # Cpython
            tzname, sign, d_hour, d_min, d_sec = x.group(1), x.group(2), x.group(3) or 0, x.group(4) or 0, x.group(5) or 0  # micropython
            offset = (int(d_hour) * 60 + int(d_min)) * 60 + int(d_sec)
            timezone = offset * (1 if sign == "-" else -1)
        else:
            tzname = s
            timezone = 0
        return tzd_tuple(tzname, timezone, None, None, None, None)
    if len(ss) == 3:
        # FIXME refactor, remove duplication
        x = re.match(name_offset_re, ss[0])
        tzname, sign, d_hour, d_min, d_sec = x.group(1), x.group(2), x.group(3) or 0, x.group(4) or 0, x.group(5) or 0  # micropython
        offset = (int(d_hour) * 60 + int(d_min)) * 60 + int(d_sec)
        timezone = offset * (1 if sign == "-" else -1)
        # TODO parse DST name and offset, for now default
        return tzd_tuple(tzname, timezone, '?DST?', parse_mstr(ss[1]), parse_mstr(ss[2]), timezone + 1 * 60 * 60)
    else:
        NotImplementedError('FIXME for %r)' %s)

def determine_change(p, year, offset):
    """
    Mm.n.d format, where:

        Mm (1-12) for 12 months
        n (1-5) 1 for the first week and 5 for the last week in the month
        d (0-6) 0 for Sunday and 6 for Saturday

    For example:
        PST8PDT,M3.2.0/2:00:00,M11.1.0/2:00:00
    
      * PST8PDT
      * M3.2.0/2:00:00
          * 3 - March
          * 2 - 2nd week
          * 0 - Sunday
          * 2:00:00 - 2am
      * M11.1.0/2:00:00

    offset - offsets are seconds
    """
    month, occur, day, h, min, sec = p
    min_offset = offset // 60
    h, min = (h - (min_offset // 60)), (min - (min_offset % 60))

    month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if ((((year % 4) == 0) and ((year % 100) != 0)) or (year % 400) == 0):
        month_days[1] = 29

    # Gauss date algo, determine day of week for first day of the month
    d = 1
    x = year - ((14 - month) // 12)
    y = (x + (x // 4)) - ((x // 100)) + ((x // 400))
    z = month + 12 * ((((14 - month)) // 12)) - 2;
    first_dom = (d + y + ((31 * z) // 12)) % 7
    #print('Gauss first of the %r month %r' % (month, first_dom))

    # determine the day of the month
    dom = 1 + (occur - 1) * 7 + (day - first_dom) % 7

    if dom > month_days[month - 1]:
        dom -= 7
    
    tr = time.mktime((year, month, dom, h, min, sec, 0, 0, 0))  # NOTE 9 params for CPython... 8 for MicroPython - this is the GMT0 time
    return tr  # NOTE for CPython, DST start time could be off an hour... Fine in Micropython


def set_tz(tz):
    global global_tzd
    global_tzd = parse_tz(tz)

_localtime_cache = {}  # rather than require functool lru (which is not built into MicroPython), cache manually with no clean up. Assume use case doesn't span hundreds of years
def localtime(n=None, tzd=None):
    if n is None:
        n = time.time()
    tzd = tzd or global_tzd

    if tzd:
        time_tuple = time.gmtime(n)
        year = time_tuple[0]  # FIXME, assume DST never starts/ends on first/last day of a year - probably a safe thing todo
        #start_date, end_date = _localtime_cache.get((tzd.start, year), determine_change(tzd.start, year)), _localtime_cache.get((tzd.end, year), determine_change(tzd.end, year)
        try:
            start_date, end_date = _localtime_cache[(tzd.start, year)], _localtime_cache[(tzd.end, year)]
        except KeyError:
            start_date, end_date = determine_change(tzd.start, year, tzd.offset), determine_change(tzd.end, year, tzd.dst_offset)
            _localtime_cache[(tzd.start, year)], _localtime_cache[(tzd.end, year)] = start_date, end_date
        if start_date < n < end_date:
            n += tzd.dst_offset
        else:
            n += tzd.offset
    # else assume UTC/GMT0
    return time.localtime(n)

def debug_localtime():
    t = time.time()
    print(t)
    print(parse_tz('PST8PDT,M3.2.0,M11.1.0'))
    print(parse_tz('PST8PDT,M3.2.0/2:00:00,M11.1.0/2:00:00'))

    parsed = parse_tz('PST8PDT,M3.2.0,M11.1.0')
    start_date = determine_change(parsed.start, 2025)
    end_date = determine_change(parsed.end, 2025)
    print(time.localtime(start_date), start_date)
    print(time.localtime(end_date), end_date)

#debug_localtime()
