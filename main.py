#!/usr/bin/env python
#coding:utf-8
import re
import os
import sys
import json
import hashlib
from ebooklib import epub
from PyPDF2 import PdfFileReader
from PyPDF2.generic import IndirectObject, TextStringObject

def main(option):
    """
    """
    metas = read_old_meta()
    for dir_meta in metas:
        dir_name = dir_meta['dir_name']
        print("reads: " + dir_name)
        books = {}
        if 'books' in dir_meta:
            old_books = dir_meta['books']
        else:
            old_books = None
        for f in os.listdir(dir_name):
            file_name = os.path.join(dir_name, f)
            if os.path.isfile(file_name):
                # hash_str = subprocess.check_output(['sha256sum', file_name])
                # hash_sum = hash_str.decode().split(" ")[0]
                hash_sum = file_sha256(file_name)
                if '-f' not in option and old_books and f in old_books and old_books[f]['sha_256'] == hash_sum:
                    meta = old_books[f]
                    print("--read meta miss: " + f)
                elif f.endswith('.pdf'):
                    print("--read meta: " + f)
                    meta = read_meta_pdf(file_name)

                elif f.endswith('.epub'):
                    print("--read meta: " + f)
                    meta = read_meta_epub(file_name)
                meta['sha_256'] = hash_sum
                books[f] = meta
        dir_meta['books'] = books
    save_old_meta(metas)

    print("------complete------")
    # metas = []
    # for fd in tree_dir("."):
    #     print(fd)
    #     hash_str = subprocess.check_output(['sha512sum', fd])
    #     hash_sum = hash_str.decode().split(" ")[0]
    #     if fd.endswith('.pdf'):
    #         try:
    #             meta = read_meta_pdf(fd)
    #         except:
    #             meta = {}
    #         meta['SHA512'] = hash_sum
    #         meta['FILE'] = fd
    #     elif fd.endswith('.epub'):
    #         meta = read_meta_epub(fd)
    #     meta['SHA512'] = hash_sum
    #     meta['FILE'] = fd
    #     metas.append(meta)
    # print(metas)

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
        json.dump(data, fd)

def read_meta_epub(epub_name):
    doc = epub.read_epub(epub_name)
    doc = doc.metadata['http://purl.org/dc/elements/1.1/']
    DOC_KEY = '{http://www.idpf.org/2007/opf}scheme'
    for key, val in doc.items():
        if 'identifier' == key:
            identifier = {}
            for iden in val:
                iden_key = DOC_KEY if DOC_KEY in iden[1] else 'id'
                identifier[iden[1][iden_key]] = iden[0]
            doc[key] = identifier
        else:
            if len(val) == 1:
                doc[key] = val[0][0]
            else:
                doc[key] = [value[0] for value in val if len(value) > 0]
    return doc

def tree_dir(dir_name, level=0):
    dir_list = os.listdir(dir_name)
    for f in dir_list:
        if os.path.isdir(f):
            for ff in tree_dir(f, level + 1):
                yield os.path.join(dir_name, ff)
        elif f.endswith(('.pdf', '.epub')):
            yield os.path.join(dir_name, f)


if __name__ == "__main__":
    option = set(sys.argv[1:])
    main(option)
    #read_meta_pdf("android/Android高薪之路：Android程序员面试宝典.pdf")

