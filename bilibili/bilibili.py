# -*- coding: utf-8 -*-
import os
import re
import sys
import csv
import time
import json
import random
import datetime
import argparse
import tempfile
import traceback


def sb_wrong(config):
    print('Bad command')

def sb_export(config):
    """Share Blocking Records Export"""
    print('TODO...')

def sb_import(config):
    """Share Blocking Records Export"""
    print('TODO...')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', help='export/import/merge')
    parser.add_argument('-A', default='', help='append csv file', metavar='FILE', dest='append')
    parser.add_argument('-O', default='bilibili.csv', help='export csv file', dest='file')
    parser.add_argument('-I', default='https:///', help='import csv file', dest='load')
    parser.add_argument('-C', default='config.json', help='json config file', metavar='FILE', dest='config')
    parser.add_argument('-N', default=0, type=int, help='how many pages', dest='pages')
    parser.add_argument('--desc', action='store_true', help='keep desc timeline without reverse')
    parser.add_argument('--cookie', default='', help='cookie string or cookie file', metavar='')
    args = parser.parse_args()
    globals().get('sb_{args.command}'.format(args=args),sb_wrong)(args)

