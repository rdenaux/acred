#
# 
#
"""
Utility for measuring and reporting timings
"""
from datetime import datetime


esi_context = 'http://expertsystem.com'


def start():
    """Start a timings measurement
    To be used in combination with `timings`

    :returns: a datetime
    :rtype: datetime
    """
    return datetime.now()


def _millis_from(start):
    dt = datetime.now() - start
    secs = (dt.days * 24 * 60 * 60 + dt.seconds)
    ms = secs * 1000 + dt.microseconds / 1000.0
    return int(ms)


def timing(phase, start, subts=[]):
    """Create a Timing dict for phase with the time it took since start

    :param phase: Name of the phase for this Timing
    :param start: datetime when this timing started
    :param subts: any sub Timing dicts, provides further information
      about subphases and their timings
    :returns: a Timing dict
    :rtype: dict
    """
    return {
        '@context': esi_context,
        '@type': 'Timing',
        'phase': phase,
        'total_ms': _millis_from(start),
        'sub_timings': subts
    }
