import numpy as np
import os, sys, glob
import csv, json
import pandas as pd
import meme.archive
from datetime import datetime


def meme_time(year,month,day):
    """Get time format for meme"""
    return datetime(year,month,day)


