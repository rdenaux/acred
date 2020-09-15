#!python3
""" Run claimencoder API Server as UWSGI App"""
import builtins

from claimencoder import app as application

if __name__ == "__main__":
    application.run()
