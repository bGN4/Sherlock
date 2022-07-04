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
from io import open
from lxml import etree
import requests


PY2 = sys.version_info.major==2
if PY2:
    reload(sys)
    sys.setdefaultencoding('utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))
print( 'PWD=%s'%os.path.abspath(os.curdir) )
project_url = 'https://github.com/bGN4/Sherlock'
export_url = 'https://localhost/test/export?page=%d'
import_url = 'https://localhost/test/import?uid=%s'
remove_url = 'https://localhost/test/remove?uid=%s'
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 5_0 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Mobile/9A334',
}


def import_single_user(uid):
    url = import_url%uid
    headers['Referer'] = url.replace('act=addbc&', '')
    r = r302 = requests.get(url, headers=headers, allow_redirects=False)
    return r.status_code
    if r.status_code == 302:
        url = 'https://weibo.cn' + r302.headers['Location']
        r = requests.get(url, headers=headers)
        selector = etree.HTML(r.content)
        result = selector.xpath('//div[@class="ps"]/text()')
        if len(result)>0:
            return result[0]
        return r302.headers['Location']
    return r.status_code

def remove_single_user(uid):
    url = remove_url%uid
    headers['Referer'] = url.replace('act=delbc&','').replace('rl=0&','').replace('&st=','&rl=&st=')
    r = r302 = requests.get(url, headers=headers, allow_redirects=False)
    return r.status_code

def web_load(func):
    def wrapper(path):
        if 'https:///' == path: path = 'https://raw.githubusercontent.com/bGN4/Sherlock/master/weibo.csv'
        if not re.match(r'(http|ftp)s?://', path):
            return func(path)
        ((f,path), url) = (tempfile.mkstemp(suffix='.csv'), path)
        os.close(f)
        try:
            print( 'Download: %s'%url )
            content = requests.get(url).content
            with open(path, 'wb') as f:
                f.write( content )
            print( 'Tempfile: %s'%path )
        except Exception as e:
            os.remove(path)
            if not type(e).__module__.startswith('requests.'):
                raise
            print(u'下载失败，请稍后再试或改为使用本地文件。(%s)'%type(e).__name__)
            print(u'小提示：食用佛跳墙增加智力后下载成功率会大大提高～')
        result = func(path)
        os.remove(path)
        return result
    return wrapper

@web_load
def do_load(path):
    if not os.path.exists(path): return (None, None)
    print( 'Loading: %s'%path )
    (rows, maps, lines) = ([], {}, 0)
    with open(path, encoding='utf-8') as f:
        for row in csv.reader(f):
            lines += 1
            if not row[0].isdigit() and lines>1:
                print( 'Skip line {}: {}'.format(lines,row) )
                continue
            maps[row[0]] = len(rows)
            rows.append(row)
    print( '========== Loaded {} rows from {} lines =========='.format(len(rows),lines) )
    assert( len(rows)==len(maps) )
    return (rows, maps)

def do_reverse(path, backup):
    os.rename(path, backup)
    with open(path,'wb') as asc, open(backup,'rb') as desc:
        lines = desc.readlines()
        asc.writelines( reversed(lines) )
        print( '========== Reverse all %d records with timeline. =========='%len(lines) )
    os.remove(backup)

def sb_wrong(args, config):
    print('Bad command')

def sb_remove(args, config):
    print('TODO...')

def sb_clean(args, config):
    print('TODO...')

def sb_export(args, config):
    """Share Blocking Records Export"""
    print('TODO...')

def sb_import(args, config):
    """Share Blocking Records Import"""
    (rows, maps) = do_load(args.load)
    (add, amount, total) = (0, 0, len(rows))
    selector = fetch_html( export_url.split('&',1)[0] )
    latest = (export_single_page(selector)+[None])[0]
    index = maps[latest[0]] if latest is not None else -1
    for (i,row) in enumerate(rows):
        amount += 1
        if i<=index or 'uid'==row[0] or row[-1]<'2013': continue
        if True or add>0: time.sleep(random.randint(3, 9))
        sys.stdout.write( '[%d/%d] Blocking @%s'%(i+1,total,row[0]) )
        result = import_single_user(row[0])
        print( '\t(%s)'%result )
        add += 1
    print( '========== Finish process %d/%d user. =========='%(add,amount) )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', help='export/import/merge/remove/clean')
    parser.add_argument('-A', default='', help='append csv file', metavar='FILE', dest='append')
    parser.add_argument('-O', default='weibo.csv', help='export csv file', dest='file')
    parser.add_argument('-I', default='https:///', help='import csv file', dest='load')
    parser.add_argument('-C', default='config.json', help='json config file', metavar='FILE', dest='config')
    parser.add_argument('-N', default=0, type=int, help='how many pages', dest='pages')
    parser.add_argument('-U', default='0', help='UID', metavar='UID', dest='uid')
    parser.add_argument('--desc', action='store_true', help='keep desc timeline without reverse')
    parser.add_argument('--cookie', default='', help='cookie string or cookie file', metavar='')
    args = parser.parse_args()
    with open(args.config) as f:
        config = json.loads(f.read())
        headers = config['headers']
        assert( 'Cookie' in headers )
        export_url = config['export_url']
        import_url = config['import_url']
        remove_url = config['remove_url']
    globals().get('sb_{args.command}'.format(args=args),sb_wrong)(args, config)

