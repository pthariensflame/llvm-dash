#!/usr/bin/env python
import argparse

import sqlite3, os, subprocess
from bs4 import BeautifulSoup as bs
from shutil import rmtree
from builtins import object
from builtins import str

parser = argparse.ArgumentParser(description='Initializes docset database')
parser.add_argument('docset', type=string, help='The name of the docset', default='LLVM.docset')
parser.add_argument('docset-root', dest='docset_root', type=string, help='The path to the docset directory', required=True)
parser.add_argument('llvm-version', dest='llvm_version', type=string, help='The LLVM version for this docset', required=True)
parser.add_argument('llvm-source', dest='llvm_source', type=string, help='The path to the LLVM source directory', required=True)

class DoxygenIndexer(object):
    def __init__(self, index, **kwargs):
        self.index = index
        self.root = kwargs.get('root')
        tagfile = os.path.join(self.root, 'llvm.tags')
        self.enabled = os.path.exists(tagfile)
        if self.enabled:
            self.tagfile = open(tagfile, 'r')
            self.tags = bs(self.tagfile, 'lxml-xml')
        self.tag_handlers = {
            'file', fileHandler(**kwargs),
            'namespace', namespaceHandler(**kwargs),
            'class': classHandler(**kwargs),
            'struct', structHandler(**kwargs),
            'union', unionHandler(**kwargs),
            'function', functionHandler(**kwargs),
            'define', defineHandler(**kwargs),
            'enumeration', enumerationHandler(**kwargs),
            'enumvalue', enumvalueHanlder(**kwargs),
            'typedef', typedefHandler(**kwargs),
            'variable', variableHandler(**kwargs)
        }

    def run(self):
        if self.enabled:
            for tag in self.tags.recursiveChildGenerator():
                for handler in self.tag_handlers.values():
                    entry = handler.handle(tag)
                    if entry is not None:
                        self.index.insert_entry(entry)

class Handler(object):
    def get_name(self, tag):
        return tag.findChild('name').contents[0]

    def get_type(self, tag):
        pass

    def get_path(self, tag):
        get_content = lambda item: item.contents[0] if item.contents else ''
        if tag.find('filename', recursive=False) is not None:
            return get_content(tag.filename)
        elif tag.find('anchorfile', recursive=False) is not None:
            anchorfile = get_content(tag.anchorfile)
            anchor = get_content(tag.anchor)
            return anchorfile + '#' + anchor if anchor else anchorfile

    def can_handle(self, tag):
        pass

    def handle(self, tag):
        if self.can_handle(tag):
            return (self.get_name(tag), self.get_type(tag), self.get_path(tag))
        else:
            return None

class HandlerWithTypeAndFindByNameAndKind(Handler):
    def __init__(self, type_name, tag_name, tag_kind, **kwargs):
        self.type_name = type_name
        self.tag_name = tag_name
        self.tag_kind = tag_kind

    def get_type(self, tag):
        return self.type_name

    def can_handle(self, tag):
        return tag.name == self.tag_name and tag.attrs.get('kind', '') == self.tag_kind

class HandlerWithAutoTypeAndFindByNameAndAutoKind(HandlerWithTypeAndFindByNameAndKind):
    def __init__(self, tag_name, **kwargs):
        class_name = type(self).__name__
        end_idx = class_name.rfind('Handler')
        tag_kind = str(class_name[:end_idx])
        type_name = tag_kind.capitalize()
        super(HandlerWithAutoTypeAndFindByNameAndAutoKind, self).__init__(type_name, tag_name, tag_kind, **kwargs)

class HandlerAutoWithCompoundTagName(HandlerWithAutoTypeAndFindByNameAndAutoKind):
    def __init__(self, **kwargs):
        super(HandlerAutoWithCompoundTagName, self).__init__(u'compound', **kwargs)

class HandlerAutoWithMemberTagName(HandlerWithAutoTypeAndFindByNameAndAutoKind):
    def __init__(self, **kwargs):
        super(HandlerAutoWithMemberTagName, self).__init__(u'member', **kwargs)

class fileHandler(HandlerAutoWithCompoundTagName):
    def get_path(self, tag):
        return super(fileHandler, self).get_filename(tag) + '.html'

class namespaceHandler(HandlerAutoWithCompoundTagName):
    pass

class classHandler(HandlerAutoWithCompoundTagName):
    pass

class structHandler(HandlerAutoWithCompoundTagName):
    pass

class unionHandler(HandlerAutoWithCompoundTagName):
    pass

class functionHandler(HandlerAutoWithMemberTagName):
    def __init__(self, **kwargs):
        super(functionHandler, self).__init__(**kwargs)

    def get_type(self, tag):
        if tag.findParent().get('kind') in ['class', 'struct']:
            return u'Method'
        return super(functionHandler, self).get_type(tag)

class defineHandler(HandlerAutoWithMemberTagName):
    pass

class enumerationHandler(HandlerAutoWithMemberTagName):
    def __init__(self, **kwargs):
        super(enumerationHandler, self).__init__(**kwargs)
        self.type_name = u'Enum'

class enumvalueHandler(HandlerAutoWithMemberTagName):
    def __init__(self, **kwargs):
        super(enumvalueHandler, self).__init__(**kwargs)
        self.type_name = u'Value'

class typedefHandler(HandlerAutoWithMemberTagName):
    def __init__(self, **kwargs):
        super(typedefHandler, self).__init__(**kwargs)
        self.type_name = u'Type'

class variableHandler(HandlerAutoWithMemberTagName):
    pass

class StandardIndexer(object):
    def __init__(self, index, **kwargs):
        self.index = index
        self.root = kwargs.get('root')
        self.base_path = kwargs.get('base_path', './')
        self.pages = {
            'General': 'index.html',
            'Instruction': 'ProgrammersManual.html',
            'Category': 'LangRef.html',
            'Command': 'CommandGuide/index.html',
            'Guide': 'GettingStarted.html',
            'Sample': 'tutorial/index.html',
            'Service': 'Passes.html'
        }

    def run(self):
        print('Indexing standard documentation..')
        for p in self.pages:
            category = p
            page = self.pages[p]
            html = open(output + '/' + page, 'r').read()
            self.index_page(category, page)

    def index_page(self, category, page):
        with open(os.path.join(self.root, page), 'r') as f:
            html = f.read()
            soup = bs(html)
            for a in soup.findAll('a'):
                self.index_anchor(a, category, page)

    def index_anchor(self, anchor, category, page):
        name = anchor.text.strip()
        path = anchor.get('href')
        link_class = anchor.get('class').split()

        name = name.replace('\n', '')
        filtered = ('index.html', 'http')

        is_valid_path = path is not None and not path in filtered
        is_valid_name = len(name) > 2
        is_valid_link = 'reference' in link_class

        if is_valid_path and is_valid_name and is_valid_link:
            dirpath = ['Command', 'Sample']
            if page in dirpath:
                path = page.split('/')[-2] + '/' + path
            if path.startswith('#'):
                path = base_path + page.split('/')[-1] + path
            else:
                path = base_path + path

            self.index.insert_entry((name, category, path))

class Index(object):
    def __init__(**kwargs):
        root = kwargs.get('docset_root')
        self.db_path = os.path.join([root, 'Contents', 'Resources', 'docSet.dsidx'])
        self.conn = None

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

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, etype, eval, etrace):
        self.close()

    def insert_entry(self, entry):
        self.cursor.execute('INSERT OR IGNORE INTO searchIndex(name, type, path) VALUES (?,?,?)', entry)


def write_plist(**kwargs):
    root = kwargs.get('docset_root')
    name = kwargs.get('docset_name').split('.')[0]
    llvm_version = kwargs.get('llvm_version')
    base_url = 'http://llvm.org/releases/{0}/docs/'.format(llvm_version)
    plist_path = os.path.join([root, 'Contents', 'Info.plist'])
    content = ' <?xml version=\'1.0\' encoding=\'UTF-8\'?>' \
        '<!DOCTYPE plist PUBLIC \'-//Apple//DTD PLIST 1.0//EN\' \'http://www.apple.com/DTDs/PropertyList-1.0.dtd\'> ' \
        '<plist version=\'1.0\'> ' \
        '<dict> ' \
        '    <key>CFBundleIdentifier</key> ' \
        '    <string>{0}</string> ' \
        '    <key>CFBundleName</key> ' \
        '    <string>{1}</string>' \
        '    <key>DocSetPlatformFamily</key>' \
        '    <string>{2}</string>' \
        '    <key>isDashDocset</key>' \
        '    <true/>' \
        '    <key>isJavaScriptEnabled</key>' \
        '    <true/>' \
        '    <key>dashIndexFilePath</key>' \
        '    <string>{3}</string>' \
        '    <key>DashDocSetFallbackURL</key>' \
        '    <string>{4}</string>' \
        '</dict>' \
        '</plist>'.format(name, name, name, 'index.html', base_url)
    with open(plist_path, 'w') as plist:
        plist.write(content)

if __name__ == '__main__':
    args = parser.parse_args()
    db_path = args.docset_root + '/Contents/Resources/docSet.dsidx'

    # Create index
    with Index(**args) as index:
        # Index standard documentation
        std = StandardIndexer(index, **args)
        std.run()

        # Index Doxygen-generated docs
        dox = DoxygenIndexer(index, **args)
        dox.run()

    # Generate Info.plist
    write_plist(**args)
