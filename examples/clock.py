"""Time and date, centred. The plainest useful display."""
import datetime

from muntin import canvas as cv
from muntin import scene as sc


def render():
    now = datetime.datetime.now()
    return sc.Column([
        sc.Text(now.strftime("%H:%M"), font="spleen-5x8", color=cv.WHITE),
        sc.Text(now.strftime("%a %d %b").upper(), color=cv.DIM),
    ], gap=2, align="center", justify="center")
