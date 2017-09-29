#!/usr/bin/env python
#coding:utf-8
import re
import os
import sys
import json
import hashlib
from urllib import parse
from ebooklib import epub
from PyPDF2 import PdfFileReader
from PyPDF2.generic import IndirectObject, TextStringObject

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
            format_arr.append('\n    - [豆瓣](https://book.douban.com/subject/%s)' % val)
        elif 'ISBN' == key:
            format_arr.append('\n    - [ISBN](https://www.worldcat.org/isbn/%s)' % val)
            # format_arr.append('\n    - [豆瓣-ISBN](https://book.douban.com/isbn/%s)' % val)
    if len(format_arr) == 0:
        return None
    return "书号　　", ''.join(format_arr)

def build_markdown(options):
    """
    通过元数据生成markdown
    """
    meta_dict = {
        'subject': "标签　　",
        'publisher': "出版社　",
        'description': "简介　　",
        'language': "国家语言",
        'creator': "创建人　",
        'date': "出版时间",
        'contributor': "创建工具",
        'identifier': identifier_format,
        'type': "文件类型",
        'creation_date': "创建时间",
        'mod_date': "修改时间",
        'producer': "制作人　",
        'rating': "评分　　"
    }
    metas = read_old_meta()
    buffer = []
    buffer.append('# TOC')
    buffer.append('\n')
    buffer.append('[TOC]')
    for book_type in metas:
        buffer.append('\n')
        buffer.append('## %s' % (book_type['dir_name']))
        buffer.append('> [📚%s](%s)' % (book_type['name'], book_type['dir_name']))
        for book in book_type['books']:
            book_name = book['file']
            title = book['title'] if 'title' in book and book['title'].strip() != '' else book_name
            buffer.append('\n')
            buffer.append('### %s' % title)
            buffer.append('[📖%s](%s) [📥下载](../../info/lfs/objects/%s/%s)' % (title, book_type['dir_name'] + '/' + book_name, book['sha_256'], book_name))
            for key, item in book.items():
                if key in meta_dict:
                    handle = meta_dict[key]
                    if isinstance(handle, str):
                        buffer.append('- %s: %s' % (handle, item))
                    else:
                        str1 = handle(item)
                        if str1:
                            buffer.append('- %s: %s' % str1)

    with open('TOC.md', 'w') as fd:
        fd.write("\n".join(buffer))
        

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
                    print("|--read meta: " + f)
                    meta = read_meta_pdf(file_name)
                    meta['type'] = 'pdf'
                elif f.endswith('.epub'):
                    print("|--read meta: " + f)
                    meta = read_meta_epub(file_name)
                    meta['type'] = 'epub'
                else:
                    meta = None
                if meta:
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
        return new_info

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
                identifier[iden[1][iden_key]] = iden[0]
            meta[key] = identifier
        else:
            if len(val) == 1:
                meta[key] = val[0][0]
            else:
                meta[key] = [value[0] for value in val if len(value) > 0]
    return meta

if __name__ == "__main__":
    options = set(sys.argv[1:])
    main(options)
    # read_meta_epub('cvs/progit2.epub')
    #read_meta_pdf("android/Android高薪之路：Android程序员面试宝典.pdf")

