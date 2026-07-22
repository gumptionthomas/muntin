"""A label, a current value, and a trend line under both."""
from muntin import canvas as cv
from muntin import scene as sc

SERIES = [3, 5, 4, 8, 6, 9, 12, 11, 14, 13, 17, 16, 20, 19, 22]


def render():
    return sc.Column([
        sc.Row([
            sc.Text("REQS/S", color=cv.DIM),
            sc.Text(str(SERIES[-1]), color=cv.WHITE),
        ], gap=4, justify="center"),
        sc.Plot(SERIES, color=cv.GREEN),
    ], gap=3, align="center", justify="center")
