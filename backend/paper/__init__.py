"""Forward paper-trading layer for the FROZEN F+ engine (commit 57e72d5).

Reuses F+'s decision functions verbatim (selection / graded exposure / breakdown)
and executes them against real EOD prices with a Rs 10,00,000 book, persisting an
immutable forward track record. The F+ backtest engine is NOT modified.
"""
