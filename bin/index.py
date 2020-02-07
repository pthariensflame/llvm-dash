#!/usr/bin/env python
"""index.py - Generates sqlite3 index for docset documentation"""
from __future__ import absolute_import
from builtins import object
from builtins import str
import sqlite3
import os
import io
import sys
import argparse
import bs4
from bs4 import BeautifulSoup as bs

PARSER = argparse.ArgumentParser(description='Initializes docset database')
PARSER.add_argument('--debug', \
        default=False, \
        help='Enable debugging output', \
        action='store_true')
PARSER.add_argument('--docset', \
        help='The name of the docset', \
        default='LLVM.docset')
PARSER.add_argument('--docset-root', \
        dest='docset_root', \
        help='The path to the docset directory', \
        required=True)
PARSER.add_argument('--llvm-version', \
        dest='llvm_version', \
        help='The LLVM version for this docset', \
        required=True)
PARSER.add_argument('--llvm-source', \
        dest='llvm_source', \
        help='The path to the LLVM source directory', \
        required=True)
PARSER.add_argument('--no-doxygen', \
        dest='no_doxygen', \
        default=False,
        help='Do not index Doxygen documentation', \
        action='store_true')
PARSER.add_argument('--no-std', \
        dest='no_std', \
        default=False,
        help='Do not index standard documentation', \
        action='store_true')

class DoxygenIndexer(object):
    def __init__(self, index, documents_dir, **kwargs):
        print('Indexing Doxygen-generated docs..')
        self.index = index
        self.root = os.path.join(documents_dir, 'doxygen')
        tagfile = os.path.join(self.root, 'llvm.tags')
        self.enabled = os.path.exists(tagfile)
        if self.enabled:
            self.tagfile = io.open(tagfile, 'r', encoding='utf-8')
            self.tags = bs(self.tagfile, 'lxml-xml')
        else:
            print('Doxygen docs are disabled, no tagfile found')
        self.tag_handlers = {}
        self.tag_handlers['file'] = FileHandler(self, **kwargs)
        self.tag_handlers['namespace'] = NamespaceHandler(self, **kwargs)
        self.tag_handlers['class'] = ClassHandler(self, **kwargs)
        self.tag_handlers['struct'] = StructHandler(self, **kwargs)
        self.tag_handlers['union'] = UnionHandler(self, **kwargs)
        self.tag_handlers['function'] = FunctionHandler(self, **kwargs)
        self.tag_handlers['define'] = DefineHandler(self, **kwargs)
        self.tag_handlers['friend'] = FriendHandler(self, **kwargs)
        self.tag_handlers['enumeration'] = EnumerationHandler(self, **kwargs)
        self.tag_handlers['enumvalue'] = EnumValueHandler(self, **kwargs)
        self.tag_handlers['typedef'] = TypedefHandler(self, **kwargs)
        self.tag_handlers['variable'] = VariableHandler(self, **kwargs)
        self.tag_handlers['group'] = GroupHandler(self, **kwargs)
        self.tag_handlers['page'] = PageHandler(self, **kwargs)

    def insert_entry(self, name, ty, path):
        path = os.path.join('doxygen', path)
        self.index.insert_entry((name, ty, path))

    def run(self):
        if self.enabled:
            for tag in self.tags.tagfile.children:
                if type(tag) == bs4.element.NavigableString:
                    continue
                self.index_tag(tag)
            print('')

    def index_tag(self, tag):
        tagkind = tag['kind']
        handler = self.tag_handlers[tagkind]
        if handler is not None:
            handler.handle(tag)
        else:
            print('Unhandled tag kind ({}) for: {}'.format(tagkind, tag))

class Handler(object):
    def __init__(self, indexer, **kwargs):
        self.indexer = indexer
        self.args = kwargs

    @staticmethod
    def get_contents(item):
        if item is None:
            return None
        return item.contents[0]

    def get_name(self, tag):
        return self.get_contents(tag.find('name', recursive=False))

    def get_type(self, tag):
        return tag['kind'].capitalize()

    def get_path(self, tag):
        filename = tag.find('filename', recursive=False)
        path = self.get_contents(filename)
        if path is None:
            anchorfile = tag.find('anchorfile', recursive=False)
            path = self.get_contents(anchorfile)
        if not path.endswith('.html'):
            path = path + '.html'
        anchor = tag.find('anchor', recursive=False)
        if anchor is not None:
            return path + '#' + self.get_contents(anchor)
        else:
            return path

    def insert_entry(name, ty, path):
        self.indexer.insert_entry(name, ty, path)
        return

    def handle(self, tag):
        name = self.get_name(tag)
        ty = self.get_type(tag)
        path = self.get_path(tag)
        self.indexer.insert_entry(name, ty, path)
        return

class FileHandler(Handler):
    def handle(self, tag):
        super(FileHandler, self).handle(tag)
        for tag in tag.findChildren('member', recursive=False):
            self.indexer.index_tag(tag)
        return

class MemberHandler(Handler):
    def get_path(self, tag):
        filename = self.get_contents(tag.find('anchorfile', recursive=False))
        anchor = tag.find('anchor', recursive=False)
        if anchor is not None:
            return filename + '#' + self.get_contents(anchor)
        else:
            return filename

class FunctionHandler(MemberHandler):
    def get_type(self, tag):
        if tag.findParent().get('kind') in ['class', 'struct']:
            return u'Method'
        return super(FunctionHandler, self).get_type(tag)

class DefineHandler(MemberHandler):
    pass

class EnumerationHandler(MemberHandler):
    pass

class EnumValueHandler(MemberHandler):
    pass

class TypedefHandler(MemberHandler):
    def get_type(self, tag):
        return u'Type'

class FriendHandler(MemberHandler):
    def handle(self, tag):
        return

class VariableHandler(MemberHandler):
    def handle(self, tag):
        return

class NamespaceHandler(Handler):
    def handle(self, tag):
        super(NamespaceHandler, self).handle(tag)
        for tag in tag.findChildren('struct', recursive=False):
            self.indexer.index_tag(tag)
        for tag in tag.findChildren('class', recursive=False):
            self.indexer.index_tag(tag)
        for tag in tag.findChildren('member', recursive=False):
            self.indexer.index_tag(tag)
        return

class GroupHandler(Handler):
    def handle(self, tag):
        return

class PageHandler(Handler):
    def handle(self, tag):
        return

class StructuredTypeHandler(Handler):
    def handle(self, tag):
        if tag.find('name', recursive=False) is None:
            return
        if tag.find('filename', recursive=False) is None:
            return
        super(StructuredTypeHandler, self).handle(tag)
        for tag in tag.findChildren('member', recursive=False):
            self.indexer.index_tag(tag)
        return

class ClassHandler(StructuredTypeHandler):
    pass

class StructHandler(StructuredTypeHandler):
    pass

class UnionHandler(StructuredTypeHandler):
    pass

class StandardIndexer(object):
    def __init__(self, index, documents_dir, **kwargs):
        self.index = index
        self.root = documents_dir
        self.categories = {
            'General': self.handle_general,
            'Instruction': self.handle_reference,
            'Section': self.handle_langref,
            'Command': self.handle_commands,
            'Guide': self.handle_guide,
            'Sample': self.handle_tutorial,
            'Plugin': self.handle_passes
        }

    def run(self):
        print('Indexing standard documentation..')
        for c in self.categories:
            handler = self.categories[c]
            handler()
        print('')

    def handle_general(self):
        with io.open(os.path.join(self.root, 'index.html'), 'r', encoding='utf-8') as f:
            html = f.read()
            soup = bs(html, features='html.parser')
            for a in soup.select('#user-guides .docutils a.reference.internal'):
                self.index_anchor(a, 'Guide', 'index.html')
            for a in soup.select('#programming-documentation .docutils a.reference.internal'):
                self.index_anchor(a, 'Instruction', 'index.html')
            for a in soup.select('#subsystem-documentation .docutils a.reference.internal'):
                self.index_anchor(a, 'Instruction', 'index.html')
            for a in soup.select('#development-process-documentation .docutils a.reference.internal'):
                self.index_anchor(a, 'Instruction', 'index.html')

    def handle_reference(self):
        page = 'ProgrammersManual.html'
        with io.open(os.path.join(self.root, page), 'r', encoding='utf-8') as f:
            html = f.read()
            soup = bs(html, features='html.parser')
            for a in soup.select('#contents a.reference.internal'):
                self.index_anchor(a, 'Instruction', page)

    def handle_langref(self):
        page = 'LangRef.html'
        with io.open(os.path.join(self.root, page), 'r', encoding='utf-8') as f:
            html = f.read()
            soup = bs(html, features='html.parser')
            for a in soup.select('#contents a.reference.internal:not([href^="#id"])'):
                self.index_anchor(a, 'Section', page)

    def handle_commands(self):
        page = 'CommandGuide/index.html'
        with io.open(os.path.join(self.root, page), 'r', encoding='utf-8') as f:
            html = f.read()
            soup = bs(html, features='html.parser')
            for a in soup.select('#basic-commands a.reference.internal'):
                self.index_anchor(a, 'Command', page)
            for a in soup.select('#debugging-tools a.reference.internal'):
                self.index_anchor(a, 'Command', page)
            for a in soup.select('#developer-tools a.reference.internal'):
                self.index_anchor(a, 'Command', page)

    def handle_guide(self):
        self.index_page('Guide', 'GettingStarted.html')

    def handle_tutorial(self):
        page = 'tutorial/index.html'
        with io.open(os.path.join(self.root, page), 'r', encoding='utf-8') as f:
            html = f.read()
            soup = bs(html, features='html.parser')
            for toc in soup.select('.section[id] .toctree-wrapper'):
                section = toc.parent
                title = section.h2.text[:-1]
                if toc.ul is None:
                    continue
                for chapter in toc.ul.children:
                    if not isinstance(chapter, bs4.element.Tag):
                        continue
                    if not chapter.name == "li":
                        continue
                    a = chapter.a
                    name_parts = a.string.split(': ')
                    without_prefix = name_parts[1:]
                    chapter_num = name_parts[0].split('.')[0]
                    name = u'{0} - {0}. {1}'.format(title, chapter_num, ': '.join(without_prefix))
                    link = a.get('href')
                    path = self.resolve_path(page, link)
                    if path is not None:
                        self.index.insert_entry((name, 'Sample', path))

    def handle_passes(self):
        self.index_page('Plugin', 'Passes.html')

    def index_page(self, category, page):
        with io.open(os.path.join(self.root, page), 'r', encoding='utf-8') as f:
            html = f.read()
            soup = bs(html, features='html.parser')
            for a in soup.select('#contents a.reference.internal[href]'):
                self.index_anchor(a, category, page)

    def index_anchor(self, anchor, category, page, **kwargs):
        path = anchor.get('href')
        name = kwargs.get('name')
        if name is None:
            name = self.get_anchor_name(anchor)
        path = self.resolve_path(page, path)
        if path is not None:
            self.index.insert_entry((name, category, path))

    def get_anchor_name(self, anchor):
        name = self.stringify_contents(anchor)
        return name.replace('\n', '')

    def stringify_contents(self, item):
        if isinstance(item, str):
            return item
        s = item.string
        if s is not None:
            return s
        parts = []
        for p in item.contents:
            parts.append(self.stringify_contents(p))
        return ''.join(parts)

    @staticmethod
    def is_valid_path(path, **kwargs):
        if path is not None:
            filtered = kwargs.get('filtered', ('index.html'))
            return not path.startswith(filtered)
        return False

    def resolve_path(self, page, path, **kwargs):
        filtered = kwargs.get('filtered', ('index.html'))
        if not self.is_valid_path(path, filtered=filtered):
            return None
        base = os.path.basename(page)
        resolved_dir = os.path.join(self.root, os.path.dirname(page))
        normalized = ''
        if path.startswith('#'):
            normalized = os.path.normpath(os.path.join(resolved_dir, base)) + path
        else:
            normalized = os.path.normpath(os.path.join(resolved_dir, path))
        return os.path.relpath(normalized, self.root)

class Index(object):
    def __init__(self, resources_dir, **kwargs):
        self.db_path = os.path.join(resources_dir, 'docSet.dsidx')
        self.debug = kwargs.get('debug')
        self.conn = None
        self.cursor = None
        self.entries = 0

    def open(self):
        if self.conn is not None:
            self.close()
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

        self.cursor.execute('CREATE TABLE IF NOT EXISTS searchIndex(id INTEGER PRIMARY KEY, name TEXT, type TEXT, path TEXT);')
        self.cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS anchor ON searchIndex (name, type, path);')

    def close(self):
        conn = self.conn
        if conn is not None:
            conn.commit()
            conn.close()
            self.conn = None
            self.cursor = None
            self.entries = 0

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, etype, evalue, etrace):
        self.close()

    def reset_counter(self):
        self.entries = 0

    def insert_entry(self, entry):
        entries = self.entries + 1
        self.entries = entries
        if self.debug:
            print(u'Inserting entry: {0}'.format(entry))
        else:
            sys.stdout.write(u'\u001b[1000DIndexed {0} entries'.format(entries))
            sys.stdout.flush()
        self.cursor.execute('INSERT OR IGNORE INTO searchIndex(name, type, path) VALUES (?,?,?)', entry)

class Indexer(object):
    def __init__(self, args):
        self.args = args
        self.no_std = args.get('no_std', False)
        self.no_doxygen = args.get('no_doxygen', False)
        self.index = None

    def run(self):
        args = self.args
        # Index standard documentation
        if not self.no_std:
            std = StandardIndexer(self.index, **args)
            std.run()
        # Index Doxygen-generated docs
        if not self.no_doxygen:
            dox = DoxygenIndexer(self.index, **args)
            dox.run()

    def __enter__(self):
        if self.index is not None:
            self.index.close()
            self.index = None
        args = self.args
        self.index = Index(**args)
        self.index.open()
        return self

    def __exit__(self, etype, evalue, etrace):
        if self.index is not None:
            self.index.close()
            self.index = None

def write_plist(contents_dir, docset, llvm_version, **kwargs):
    name = docset.split('.')[0]
    #base_url = 'http://llvm.org/releases/{0}/docs/'.format(llvm_version)
    base_url = 'file://{0}/'.format(kwargs.get('documents_dir'))
    plist_path = os.path.join(contents_dir, 'Info.plist')
    content = '<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n' \
        '<!DOCTYPE plist PUBLIC \'-//Apple//DTD PLIST 1.0//EN\' \'http://www.apple.com/DTDs/PropertyList-1.0.dtd\'>\n' \
        '<plist version=\'1.0\'>\n' \
        '<dict>\n' \
        '    <key>CFBundleIdentifier</key>\n' \
        '    <string>{0}</string>\n' \
        '    <key>CFBundleName</key>\n' \
        '    <string>{1}</string>\n' \
        '    <key>DocSetPlatformFamily</key>\n' \
        '    <string>{2}</string>\n' \
        '    <key>isDashDocset</key>\n' \
        '    <true/>\n' \
        '    <key>isJavaScriptEnabled</key>\n' \
        '    <true/>\n' \
        '    <key>dashIndexFilePath</key>\n' \
        '    <string>{3}</string>\n' \
        '    <key>DashDocSetFallbackURL</key>\n' \
        '    <string>{4}</string>\n' \
        '</dict>\n' \
        '</plist>'.format(name, name, name, 'index.html', base_url)
    with io.open(plist_path, 'w', encoding='utf-8') as plist:
        plist.write(content)

if __name__ == '__main__':
    ARGS = vars(PARSER.parse_args())
    ARGS['docset_root'] = os.path.normpath(ARGS['docset_root'])
    ARGS['contents_dir'] = os.path.join(ARGS['docset_root'], 'Contents')
    ARGS['resources_dir'] = os.path.join(ARGS['docset_root'], 'Contents', 'Resources')
    ARGS['documents_dir'] = os.path.join(ARGS['docset_root'], 'Contents', 'Resources', 'Documents')

    # Create index
    with Indexer(ARGS) as INDEXER:
        INDEXER.run()

    # Generate Info.plist
    write_plist(**ARGS)
