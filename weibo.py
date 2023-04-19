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
import functools
import itertools
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
idinfo_url = 'http://localhost/test/info?uid=%s'
export_url = 'http://localhost/test/export?page=%d'
import_url = 'http://localhost/test/import?uid=%s'
remove_url = 'http://localhost/test/remove?uid=%s'
follow_common_lte = 'http://localhost/test/followerscommon?uid=%s&uid%s'
follow_by_tag_lte = 'http://localhost/test/followerstagrecomm.json?uid=%s&tag=%s&uid=%s&since_id=%d'
follow_by_tag_app = 'http://localhost/test/groupsMembersByTag.json?uid=%s&tag=%s&page=%d&count=20'
headers = {
    'User-Agent': '', # fill your UA in config.json
    'Cookie': '', # fill your cookie in config.json
}


def colored(s, c=90):
    return f"\033[%dm%s\033[0m"%(c,s)

def fetch_html(url, allow_redirects=False, raw=False):
    r, selector = None, None
    try:
        r = requests.get(url, timeout=30, headers=headers, allow_redirects=allow_redirects)
        selector = r.content if raw else etree.HTML( r.content )
#       open('debug.page.html', 'wb').write( r.content )
    except:
        traceback.print_exc()
    if r and r.is_redirect and not allow_redirects and not hasattr(selector,'xpath'):
        print( 'Unexpect redirect: ' + r.headers.get('Location') )
    return selector

def fetch_json(url, allow_redirects=False):
    r, data = None, {}
    try:
        r = requests.get(url, timeout=30, headers=headers, allow_redirects=allow_redirects)
        data = r.json()
    except:
        traceback.print_exc()
    return data

def get_param_st(url):
    selector = fetch_html(url)
    settings = str((selector.xpath('//div[@class="u"]//a[contains(@href,"customize")]/@href')+[''])[0])
    st = (['']+re.findall(r'st=([a-f\d]+)',settings))[-1]
    print( 'st=%s'%st )
    return st

def get_param_st_raw(url):
    content = fetch_html(url, allow_redirects=False, raw=True)
    st = (['']+re.findall(b'st=([a-f\d]+)',content))[-1].decode()
    print( 'st=%s'%st )
    return st

def trans_human_time(s, now):
    now = datetime.datetime.now()
    whole = re.match(r'([\d :-]{19})', s)
    if whole: return whole.group(1)
    year = re.match(u'(\d+)月(\d+)日 ([\d:]+)', s)
    if year: return u'{}-{}-{} {}:00'.format(now.year, year.group(1), year.group(2), year.group(3))
    today = re.match(u'今天 ([\d:]+)', s)
    if today: return u'{}-{:02}-{:02} {}:00'.format(now.year, now.month, now.day, today.group(1))
    return u'{}-{:02}-{:02} 00:00:00'.format(now.year, now.month, now.day)

def get_page_num(selector, which='total'):
    page_text = selector.xpath('//div[@id="pagelist"]//input[@type="submit"]/following-sibling::text()')[0]
    page_list = [int(i) for i in re.search(r'(\d+)/(\d+)', page_text).groups()]
    return page_list[('current','total').index(which)]

def get_weibo_block_num(selector):
    for text in selector.xpath('//div[@class="c"]/text()'):
        result = re.search(u'将(\d+)人', text)
        if result:
            return int( result.group(1) )
    return -1

def get_local_block_num():
    pass

def export_single_page(selector):
    rows = []
    users = selector.xpath('//table/tr/td/a[not(child::img)][not(contains(@href,"attention"))]')
    total = len(users)
    for i in range(0, total):
        name = users[i].text
        sid  = re.match('/([^/]{2,})', users[i].get('href'))
        sid  = sid.group(1) if sid else ''
        uid  = re.search(r'uid=(\d+)', users[i].getparent().getchildren()[-1].get('href')).group(1)
        time = trans_human_time( users[i].getnext().xpath('following-sibling::text()')[0], None)
        rows.append( [uid, sid, name, u'', u'', time] )
        sys.stdout.write( '[%X/%X] '%(i+1,total) )
        sys.stdout.write( str([uid,sid])[:-1] )
        sys.stdout.write( ", u'" )
        sys.stdout.write( name )
        sys.stdout.write( "', " )
        print( str([u'', u'', time])[1:] )
    return rows

def import_single_user(uid):
    url = import_url%uid
    headers['Referer'] = url.replace('act=addbc&', '')
    r = r302 = requests.get(url, headers=headers, allow_redirects=False)
    return r.status_code
    if r.status_code == 302:
        url = 'https://weibo.cn' + r302.headers['Location']
        selector = fetch_html(url)
        r = None
        result = selector.xpath('//div[@class="ps"]/text()')
        if len(result)>0:
            return result[0]
        return r302.headers['Location']
    return r.status_code

def remove_single_user(uid):
    url = remove_url%uid
    headers['Referer'] = url.replace('act=delbc&','').replace('rl=0&','').replace('&st=','&rl=&st=')
    r = r302 = requests.get(url, headers=headers, allow_redirects=False)
    if r.status_code == 200:
        selector = etree.HTML(r.content)
        result = selector.xpath('//div[@class="ps"]/text()')
        if len(result)>0: print( result[0] )
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


def iter_pause(items, span=(3,7)):
    (lo, hi) = (min(span), max(span))
    pause = [lo+(hi-lo)*random.random() for _ in range(len(items)-1)]
    return itertools.zip_longest(items, pause, fillvalue=0)

def do_reverse(path, backup):
    os.rename(path, backup)
    with open(path,'wb') as asc, open(backup,'rb') as desc:
        lines = desc.readlines()
        asc.writelines( reversed(lines) )
        print( '========== Reverse all %d records with timeline. =========='%len(lines) )
    os.remove(backup)

def sb_wrong(args, config):
    print('Bad command')

def sb_pop(args, config):
    global remove_url
    count = args.pages or 1
    cursor = int(args.uid[0])
    with open(args.file, encoding='utf-8') as f:
        c = 0
        for (i,line) in enumerate(f,1):
            if i<cursor: continue
            uid = line.split(',')[0]
            ban = 'baned' if re.search('已封号', line) else ''
            if not uid.isdigit(): continue
            if i>cursor: time.sleep( random.randint(3,7) )
            content = fetch_html('https://weibo.cn/%s/operation?rl=0'%uid, allow_redirects=False, raw=True)
            delb = re.findall(b'<a href="/attention/delb?(.*?)">', content)
            if not delb:
                addb = re.findall(b'<a href="/attention/addb?(.*?)">', content)
                died = re.findall(b'<div class="ps">(.*?)</div>', content)
                if addb:
                    print( i, uid, 'not in blacklist', ban )
                if died:
                    info = fetch_html('https://weibo.cn/%s/info'%uid, allow_redirects=False, raw=True)
                    print( i, uid, died[0].decode(), ('?'*5,ban or '!'*5)[b'User does not exists' in info] )
                if not (addb or died):
                    print( i, uid, 'link not found', ban )
                continue
            st = (['']+re.findall(b'st=([a-f\d]+)',delb[0]))[-1].decode()
            remove_url = re.sub(r'st=[a-f\d]+', 'st='+st, config['remove_url'])
            res = remove_single_user( uid )
            print( i, uid, res, ban )
            c += 1
            if c>=count: break

def sb_remove(args, config):
    for (uid,t) in iter_pause(args.uid):
        res = remove_single_user( uid )
        print( uid, res )
        time.sleep(t)
    num = get_weibo_block_num( fetch_html( export_url.split('&',1)[0] ) )
    print( '%d/5000'%num )

def sb_clean(args, config):
    (rows, _) = do_load(args.file)
    line_from = args.pages
    line_to = line_from + 10
    for i,row in enumerate(rows[line_from-1:],line_from):
        url = config['home_url'] + row[0]
        selector = fetch_html( url )
        status = selector.xpath('/html/body/div[@class="me"]/text()')
        if status:
            print( '%s		-		%s	%s'%(i,url,status) )
            continue
        name = selector.xpath('//div[@class="u"]/table//span[@class="ctt"][child::a]/text()')[0]
        date_list = list(map(lambda s: trans_human_time(s,None), selector.xpath('//div[@class="c"][@id]//span[@class="ct"]/text()')))
        latest = max(date_list) if date_list else '	-	'
        print( '%s	%s	%s	%s'%(i,latest,url,name) )
        if latest.startswith('2020-'):
            res = remove_single_user(row[0])
            print(res)
        if i >= line_to: break
        time.sleep(random.randint(3,7))

def sb_merge(args, config):
    (rows_base, maps_base) = do_load(args.file)
    (rows_add, maps_add) = do_load(args.append)
    (rows_new, maps_new) = ([], {})
    for row in rows_add:
        index = maps_base.get(row[0])
        if index is not None:
            if rows_base[index][0] == row[0]:
                if rows_base[index][-1] != row[-1]:
                    print( 'Update @{} from {} to {}'.format(row[0],rows_base[index][-1],row[-1]) )
                    rows_base[index][-1] = row[-1]
            else:
                print( 'Broken data: ({},{}!={})'.format(index,rows_base[index][0],row[0]) )
        else:
            rows_new.append(row)
    rows_base.extend(sorted(rows_new, key=lambda x:datetime.datetime.strptime(x[-1],'%Y-%m-%d %H:%M:%S')))
    with open(args.file, ('w','wb')[PY2], **(({'newline':'','encoding':'utf-8'},{})[PY2])) as f:
        writer = csv.writer(f)
        writer.writerows(rows_base)
    print( '========== Merge {} + {} => {} =========='.format(len(maps_base),len(maps_add),len(rows_base)) )

def sb_export(args, config):
    """Share Blocking Records Export"""
    path = args.file
    (update, _) = do_load(path)
    if update is not None: path = args.append = args.file + '.tmp'
    with open(path, ('w','wb')[PY2], **(({'newline':'','encoding':'utf-8'},{})[PY2])) as f:
        writer = csv.writer(f)
        selector = fetch_html( export_url.split('&',1)[0] )
        page_total = args.pages or get_page_num(selector)
        writer.writerows( export_single_page(selector) )
        for page in range(2, int(page_total)+1):
            print( '========== Finish process %d/%d page. =========='%(page-1,page_total) )
            time.sleep(random.randint(6,10))
            selector = fetch_html(export_url%page)
            writer.writerows( export_single_page(selector) )
        print( '========== Finish process all %d page. =========='%(page_total) )
    if not args.desc: do_reverse(path, path+'.desc')
    if update is not None: sb_merge(args, config)
    if os.path.exists(args.append): os.remove(args.append)

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
        if True or add>0: time.sleep(random.randint(3,9))
        sys.stdout.write( '[%d/%d] Blocking @%s'%(i+1,total,row[0]) )
        result = import_single_user(row[0])
        print( '\t(%s)'%result )
        add += 1
    print( '========== Finish process %d/%d user. =========='%(add,amount) )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', help='export/import/merge/remove/clean/comment/pop')
    parser.add_argument('-A', default='', help='append csv file', metavar='FILE', dest='append')
    parser.add_argument('-O', default='weibo.csv', help='export csv file', dest='file')
    parser.add_argument('-I', default='https:///', help='import csv file', dest='load')
    parser.add_argument('-C', default='config.json', help='json config file', metavar='FILE', dest='config')
    parser.add_argument('-N', default=0, type=int, help='how many pages', dest='pages')
    parser.add_argument('-U', default=[], nargs='+', help='UID', metavar='UID', dest='uid')
    parser.add_argument('--desc', action='store_true', help='keep desc timeline without reverse')
    parser.add_argument('--cookie', default='', help='cookie string or cookie file', metavar='')
    args = parser.parse_args()
    with open(args.config, encoding='utf-8') as f:
        config = json.loads(f.read())
    headers = config['headers']
    assert( headers['User-Agent'] and headers['Cookie'] )
    export_url = config['export_url']
    import_url = config['import_url']
    remove_url = config['remove_url']
    if args.command in ('import', 'remove'):
        st = get_param_st(config['home_url'])
        export_url = re.sub(r'st=[a-f\d]+', 'st='+st, config['export_url'])
        import_url = re.sub(r'st=[a-f\d]+', 'st='+st, config['import_url'])
        remove_url = re.sub(r'st=[a-f\d]+', 'st='+st, config['remove_url'])
    globals().get('sb_{args.command}'.format(args=args),sb_wrong)(args, config)

