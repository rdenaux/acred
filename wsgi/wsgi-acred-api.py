#!python3
""" Run API Server as UWSGI App"""
import builtins

from acredapi import app as application

if __name__ == "__main__":
    application.run()
