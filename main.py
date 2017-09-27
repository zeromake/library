#!/usr/bin/env python
#coding:utf-8
import os
import subprocess
import json
import logging
from ebooklib import epub
from PyPDF2 import PdfFileReader
from PyPDF2.generic import IndirectObject

def main():
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
                hash_str = subprocess.check_output(['sha512sum', file_name])
                hash_sum = hash_str.decode().split(" ")[0]
                if old_books and f in old_books and old_books[f]['SHA512'] == hash_sum:
                    meta = old_books[f]
                    print("---read meta miss: " + f)
                elif f.endswith('.pdf'):
                    print("---read meta: " + f)
                    meta = read_meta_pdf(file_name)
                    for key, tmp in meta.items():
                        isinstance
                        if isinstance(tmp, IndirectObject):
                            print(key, ": ", tmp, " - ", "---", tmp.getObject())
                elif f.endswith('.epub'):
                    print("---read meta: " + f)
                    meta = read_meta_epub(file_name)
                books[f] = meta
        dir_meta['books'] = books
    # save_old_meta(metas)
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
        return info

def read_old_meta():
    """
    读取旧的meta数据
    """
    with open("meta.json", "r") as fd:
        return json.load(fd)

def save_old_meta(data):
    """
    读取旧的meta数据
    """
    with open("meta.json", "w") as fd:
        json.dump(data, fd)

def read_meta_epub(epub_name):
    doc = epub.read_epub(epub_name)
    return doc.metadata

def tree_dir(dir_name, level=0):
    dir_list = os.listdir(dir_name)
    for f in dir_list:
        if os.path.isdir(f):
            for ff in tree_dir(f, level + 1):
                yield os.path.join(dir_name, ff)
        elif f.endswith(('.pdf', '.epub')):
            yield os.path.join(dir_name, f)


if __name__ == "__main__":
    main()
    #read_meta_pdf("android/Android高薪之路：Android程序员面试宝典.pdf")

