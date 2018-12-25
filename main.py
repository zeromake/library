#!/usr/bin/env python
# coding:utf-8
import re
import os
import sys
import json
import hashlib
from urllib.parse import quote_plus
from lxml import etree
from ebooklib import epub
from PyPDF2 import PdfFileReader
from PyPDF2.generic import IndirectObject, TextStringObject
import requests

try:
    reload(sys)
    sys.setdefaultencoding('utf-8')
except:
    pass

CALIBRE_META = 'http://calibre.kovidgoyal.net/2009/metadata'
ELEMENTS_META = 'http://purl.org/dc/elements/1.1/'
DOC_KEY = '{http://www.idpf.org/2007/opf}scheme'


def identifier_format(identifier):
    format_arr = []
    for key, val in identifier.items():
        if 'DOUBAN' == key:
            format_arr.append(
                '\n    - [豆瓣](https://book.douban.com/subject/%s)' % val
            )
        elif 'ISBN' == key:
            format_arr.append(
                '\n    - [ISBN](https://www.worldcat.org/isbn/%s)' % val
            )
            # format_arr.append(
            #     '\n    - [豆瓣-ISBN](https://book.douban.com/isbn/%s)' % val)
    if len(format_arr) == 0:
        return None
    return "书号　　", ''.join(format_arr)


def rating_format(rating):
    average = float(rating['average'])
    return '评分　　', '暂无评分'if average == 0.0 else average


def build_markdown(options):
    """
    通过元数据生成markdown
    """
    meta_dict = {
        'subject': "标签　　",
        'publisher': "出版社　",
        'description': "简介　　",
        'summary': "简介　　",
        'price': "价格　　",
        'pages': "页数　　",
        'language': "国家语言",
        'creator': "创建人　",
        'date': "出版时间",
        'pubdate': "出版时间",
        'tags': lambda tags: (
            '标签　　',
            ' '.join(['`%s`' % row['title'] for row in tags]),
        ),
        'contributor': "创建工具",
        'identifier': identifier_format,
        'type': "文件类型",
        'creation_date': "创建时间",
        'mod_date': "修改时间",
        'producer': "制作人　",
        'author': lambda authors: (
            '作者　　',
            ' '.join(['`%s`' % row for row in authors]),
        ),
        'subtitle': "副标题　",
        'rating': rating_format,
        'alt': lambda alt: ("豆瓣地址", "[%s](%s)" % (alt, alt)),
        'series': lambda series: ('从书　　', series['title']),
        'translator': lambda translator: (
            '翻译　　',
            ' '.join(['`%s`' % row for row in translator]),
        ),
    }
    metas = read_old_meta()
    buffer = []
    tocs = []
    tocs.append('# TOC')
    tocs.append('\n')
    # buffer.append('[TOC]')
    for book_type in metas:
        buffer.append('\n')
        buffer.append('## %s' % (book_type['dir_name']))
        buffer.append(
            '> [📚%s](%s)' % (book_type['name'], book_type['dir_name'])
        )
        tocs.append('- [%s](#%s)' % (book_type['name'], book_type['dir_name']))
        for book in book_type['books']:
            book_name = book['file']
            title = book['title'] if 'title' in book and book['title'].strip() != '' else book_name
            buffer.append('\n')
            buffer.append('### %s' % title)
            encode_name = quote_plus(book_name)
            buffer.append(
                '[📖%s](%s) [📥下载](../../../../library.git/info/lfs/objects/%s/%s)' % (
                    title,
                    book_type['dir_name'] + '/' + book_name,
                    book['sha_256'],
                    encode_name
                )
            )
            toc = '    - [%s](#%s)' % (title, safe_toc(title))
            if 'rating' in book:
                star_count = book['rating']['average']
                toc += ': %s' % (star_count)
            else:
                pass
            tocs.append(toc)
            for key, item in book.items():
                if key in meta_dict:
                    handle = meta_dict[key]
                    if isinstance(handle, str):
                        if item != '':
                            buffer.append('- %s: %s' % (handle, item))
                    else:
                        str1 = handle(item)
                        if str1:
                            buffer.append('- %s: %s' % str1)
    

    with open('TOC.md', 'w') as fd:
        fd.write("\n".join(tocs))
        fd.write("\n".join(buffer))

def safe_toc(toc):
    toc = toc.lower().replace(' ', '-')
    pat = '[+:,.()（），：=－]'
    return re.sub(pat, '', toc,)
        

def build_metas(options):
    """
    读取所有数据的元数据
    """
    metas = read_old_meta()
    tocs = []
    for dir_meta in metas:
        dir_name = dir_meta['dir_name']
        print("reads: " + dir_name)
        books = []
        if 'books' in dir_meta:
            old_books = dir_meta['books']
        else:
            old_books = []
        old_sha = {book['file'] : (book['sha_256'], index) for index, book in enumerate(old_books)}
        for f in os.listdir(dir_name):
            file_name = os.path.join(dir_name, f)
            if os.path.isfile(file_name):
                # hash_str = subprocess.check_output(['sha256sum', file_name])
                # hash_sum = hash_str.decode().split(" ")[0]
                hash_sum = file_sha256(file_name)
                if '-f' not in options and old_books and f in old_sha and old_sha[f][0] == hash_sum:
                    meta = old_books[old_sha[f][1]]
                    print("|--read meta miss: " + f)
                elif f.endswith('.pdf'):
                    opf_name = os.path.join(dir_name, f[:f.rfind('.')] + '.opf')
                    if '-o' not in options and os.path.exists(opf_name):
                        print("|--read opf meta: " + f)
                        meta = read_meta_opf(opf_name)
                        if 'rating' in meta:
                            del meta['rating']
                    else:
                        print("|--read pdf meta: " + f)
                        meta = read_meta_pdf(file_name)
                    meta['type'] = 'pdf'
                elif f.endswith('.epub'):
                    print("|--read epub meta: " + f)
                    meta = read_meta_epub(file_name)
                    if 'rating' in meta:
                        del meta['rating']
                    meta['type'] = 'epub'
                else:
                    meta = None
                if meta:
                    if '-d' in options and 'identifier' in meta and 'douban' in meta['identifier']:
                        douban_id = meta['identifier']['douban']
                        douban_url = 'https://api.douban.com/v2/book/%s' % douban_id
                        print('|-- read douban meta: ', douban_url)
                        r = requests.get(douban_url)
                        douban_meta = r.json()
                        douban_meta['type'] = meta['type']
                        douban_meta['title'] = meta['title']
                        douban_meta['meta_type'] = 'douban'
                        meta = douban_meta
                    meta['sha_256'] = hash_sum
                    meta['file'] = f
                    books.append(meta)
        books.sort(key=lambda x: x['file'])
        dir_meta['books'] = books
    save_old_meta(metas)

    print("------complete------")

def main(options):
    if '-m' in options:
        build_metas(options)
    elif '-a':
        build_metas(options)
        build_markdown(options)
    else:
        build_markdown(options)

def read_meta_pdf(pdf_name):
    with open(pdf_name, 'rb') as fd:
        doc = PdfFileReader(fd)
        info = doc.documentInfo
        new_info = {}
        for key, tmp in info.items():
            key = convert(key[1:])
            if isinstance(tmp, IndirectObject):
                new_info[key] = tmp.getObject()
            elif isinstance(tmp, TextStringObject):
                new_info[key] = tmp.title()
            else:
                new_info[key] = str(tmp)
        new_info['meta_type'] = 'pdf'
        return new_info

NAMESPACES = {'XML': 'http://www.w3.org/XML/1998/namespace',
              'EPUB': 'http://www.idpf.org/2007/ops',
              'DAISY': 'http://www.daisy.org/z3986/2005/ncx/',
              'OPF': 'http://www.idpf.org/2007/opf',
              'CONTAINERNS': 'urn:oasis:names:tc:opendocument:xmlns:container',
              'DC': "http://purl.org/dc/elements/1.1/",
              'XHTML': 'http://www.w3.org/1999/xhtml'}

def read_meta_opf(opf_name):
    opf = NAMESPACES['OPF']
    dc = '{%s}' % NAMESPACES['DC']
    identifier = '{%s}scheme' % opf
    dc_len = len(dc)
    meta = {}
    with open(opf_name, 'rb') as fd:
        root = etree.parse(fd).find('{%s}metadata' % opf)
        for val in root.iterchildren():
            tag = val.tag
            if tag == '{%s}meta' % opf:
                name = val.get('name')
                name_arr = name.split(':')
                name = name_arr[1] if len(name_arr) > 1 else name
                meta[name] = val.get('content')
            elif tag.startswith(dc):
                tag = tag[dc_len:]
                if tag in ('subject', 'identifier'):
                    if tag == 'subject':
                        if tag not in meta:
                            meta[tag] = []
                        meta[tag].append(val.text)
                    else:
                        if tag not in meta:
                            meta[tag] = {}
                        meta[tag][val.get(identifier).lower()] = val.text
                else:
                    meta[tag] = val.text
    meta['meta_type'] = 'opf'
    return meta

def convert(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def read_old_meta():
    """
    读取旧的meta数据
    """
    with open("meta.json", "r") as fd:
        return json.load(fd)

def file_sha256(file_name):
    sha = hashlib.sha256()
    with open(file_name, 'rb') as fd:
        byte = fd.read(8096)
        while byte:
            sha.update(byte)
            byte = fd.read(8096)
    return sha.hexdigest()

def save_old_meta(data):
    """
    读取旧的meta数据
    """
    with open("meta.json", "w") as fd:
        json.dump(data, fd, ensure_ascii=False, indent="  ")

def read_meta_epub(epub_name):
    doc = epub.read_epub(epub_name)
    # print('-------', doc)
    meta = {}
    metadata = doc.metadata
    # for vlaues, row in metadata.items():
    #     print(vlaues)
    #     print(row)
    calibre_meta = 'calibre' if 'calibre' in metadata else CALIBRE_META
    if calibre_meta in metadata:
        calibre_metadata = metadata[calibre_meta]
        for key, item in calibre_metadata.items():
            meta[key] = item[0][1]['content']
    elements_meta = metadata[ELEMENTS_META]
    for key, val in elements_meta.items():
        if 'identifier' == key:
            identifier = {}
            for iden in val:
                iden_key = DOC_KEY if DOC_KEY in iden[1] else 'id'
                identifier[iden[1][iden_key].lower()] = iden[0]
            meta[key] = identifier
        else:
            if len(val) == 1 and key not in ('subject', 'identifier'):
                meta[key] = val[0][0]
            else:
                meta[key] = [value[0] for value in val if len(value) > 0]
    meta['meta_type'] = 'opf'
    return meta

if __name__ == "__main__":
    options = set(sys.argv[1:])
    main(options)
    # print(read_meta_opf('python/《Python Cookbook》第三版中文v2.0.0.opf'))
    # read_meta_epub('cvs/progit2.epub')
    #read_meta_pdf("android/Android高薪之路：Android程序员面试宝典.pdf")

