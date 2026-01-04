"""Shim module that exposes the visualizer app as `webapp.app:app`.

Use shiny run app to run the webapp
"""
from visualizer import app, run_visualizer

__all__ = ["app", "run_visualizer"]

if __name__ == "__main__":
    run_visualizer()
