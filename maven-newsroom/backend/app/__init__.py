"""Maven Newsroom OS — backend package.

Observability + control API that *wraps* the existing maven_instagram pipeline.
It never mutates pipeline business logic; it reads artifacts, records runs, and
streams structured events to the localhost dashboard.
"""
