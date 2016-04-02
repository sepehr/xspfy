#!/usr/bin/env python
# encoding: utf-8
"""XSPF parser

XSPF specific extension of the Universal feed parser <http://feedparser.org>
Handles XSPF 1.0 playlists <http://xspf.org/xspf-v1.html>

Required: Python 2.1 or later
Recommended: Python 2.3 or later
Recommended: CJKCodecs and iconv_codec <http://cjkpython.i18n.org/>

Command-line usage:
    ./xspfparser.py http://example.com/playlst.xspf

Library usage:
    import xspfparser
    result = xspfparser.parse(url)
"""

from feedparser import *
from feedparser import _FeedParserMixin, _XML_AVAILABLE, _BaseHTMLProcessor, _StringIO
from feedparser import _getCharacterEncoding, _open_resource, _parse_date, _debug, _toUTF8

__version__ = "1.0"
__license__ = """Copyright (c) 2002-2006, Mark Pilgrim, All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 'AS IS'
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE."""
__author__ = "James Wheare <http://jouire.com/>"
# HTTP "User-Agent" header to send to servers when downloading feeds.
# If you are embedding feedparser in a larger application, you should
# change this to your application name and URL.
USER_AGENT = "XSPFParser/%s +http://github.com/jwheare/xspfparser" % __version__

class XSPFParserDict(FeedParserDict):
    # TODO, fill out keymap
    keymap = {}
    def __getitem__(self, key):
        realkey = self.keymap.get(key, key)
        if type(realkey) == types.ListType:
            for k in realkey:
                if UserDict.has_key(self, k):
                    return UserDict.__getitem__(self, k)
        if UserDict.has_key(self, key):
            return UserDict.__getitem__(self, key)
        return UserDict.__getitem__(self, realkey)
FeedParserDict = XSPFParserDict

# TODO patch _FeedParserMixin to be friendlier for subclassing
class _XSPFParserMixin(_FeedParserMixin):
    def __init__(self, baseuri=None, baselang=None, encoding='utf-8'):
        self.namespaces['http://xspf.org/ns/0/'] = ''
        self.can_be_relative_uri.extend(['location', 'info', 'identifier', 'image', 'license'])
        
        if _debug: sys.stderr.write('initializing XSPFParser\n')
        self.playlistdata = FeedParserDict() # playlist-level data
        self.tracks = [] # list of track-level data
        _FeedParserMixin.__init__(self, baseuri, baselang, encoding)
        self.inplaylist = 0
        self.intrack = 0
        if baselang:
            self.playlistdata['language'] = baselang
    
    def unknown_starttag(self, tag, attrs):
        _FeedParserMixin.unknown_starttag(self, tag, attrs)
        if self.lang:
            if tag in ('playlist'):
                self.playlistdata['language'] = self.lang
    
    # def trackNamespace
    
    def pop(self, element, stripWhitespace=1):
        output = _FeedParserMixin.pop(self, element, stripWhitespace)
        # store output in appropriate place(s)
        if self.intrack:
            self.tracks[-1][element] = output
        elif self.inplaylist:
            context = self._getContext()
            context[element] = output
        return output
    
    def _start_playlist(self, attrsD):
        self.inplaylist = 1
        self.version = '1.0' # hard coded
    
    def _end_playlist(self):
        self.inplaylist = 0
    
    def _getContext(self):
        if self.intrack:
            context = self.tracks[-1]
        else:
            context = self.playlistdata
        return context
    
    def _start_tracklist(self, attrsD):
        self.intrack = 1
        
    def _end_tracklist(self):
        self.intrack = 0
    
    def _start_track(self, attrsD):
        self.intrack = 1
        self.tracks.append(FeedParserDict())
    
    def _end_track(self):
        self.intrack = 0
    
    def _start_info(self, attrsD):
        self.push('info', attrsD)

    def _end_info(self):
        self.pop('info')
    
    def _start_title(self, attrsD):
        self.push('title', attrsD)

    def _end_title(self):
        self.pop('title')

if _XML_AVAILABLE:
    class _StrictXSPFParser(_XSPFParserMixin, xml.sax.handler.ContentHandler):
        def __init__(self, baseuri, baselang, encoding):
            if _debug: sys.stderr.write('trying StrictXSPFParser\n')
            xml.sax.handler.ContentHandler.__init__(self)
            _XSPFParserMixin.__init__(self, baseuri, baselang, encoding)
            self.bozo = 0
            self.exc = None
        
        def startPrefixMapping(self, prefix, uri):
            self.trackNamespace(prefix, uri)
        
        def startElementNS(self, name, qname, attrs):
            namespace, localname = name
            lowernamespace = str(namespace or '').lower()
            if lowernamespace.find('backend.userland.com/rss') <> -1:
                # match any backend.userland.com namespace
                namespace = 'http://backend.userland.com/rss'
                lowernamespace = namespace
            if qname and qname.find(':') > 0:
                givenprefix = qname.split(':')[0]
            else:
                givenprefix = None
            prefix = self._matchnamespaces.get(lowernamespace, givenprefix)
            if givenprefix and (prefix == None or (prefix == '' and lowernamespace == '')) and not self.namespacesInUse.has_key(givenprefix):
                    raise UndeclaredNamespace, "'%s' is not associated with a namespace" % givenprefix
            if prefix:
                localname = prefix + ':' + localname
            localname = str(localname).lower()
            if _debug: sys.stderr.write('startElementNS: qname = %s, namespace = %s, givenprefix = %s, prefix = %s, attrs = %s, localname = %s\n' % (qname, namespace, givenprefix, prefix, attrs.items(), localname))

            # qname implementation is horribly broken in Python 2.1 (it
            # doesn't report any), and slightly broken in Python 2.2 (it
            # doesn't report the xml: namespace). So we match up namespaces
            # with a known list first, and then possibly override them with
            # the qnames the SAX parser gives us (if indeed it gives us any
            # at all).  Thanks to MatejC for helping me test this and
            # tirelessly telling me that it didn't work yet.
            attrsD = {}
            for (namespace, attrlocalname), attrvalue in attrs._attrs.items():
                lowernamespace = (namespace or '').lower()
                prefix = self._matchnamespaces.get(lowernamespace, '')
                if prefix:
                    attrlocalname = prefix + ':' + attrlocalname
                attrsD[str(attrlocalname).lower()] = attrvalue
            for qname in attrs.getQNames():
                attrsD[str(qname).lower()] = attrs.getValueByQName(qname)
            self.unknown_starttag(localname, attrsD.items())

        def characters(self, text):
            self.handle_data(text)

        def endElementNS(self, name, qname):
            namespace, localname = name
            lowernamespace = str(namespace or '').lower()
            if qname and qname.find(':') > 0:
                givenprefix = qname.split(':')[0]
            else:
                givenprefix = ''
            prefix = self._matchnamespaces.get(lowernamespace, givenprefix)
            if prefix:
                localname = prefix + ':' + localname
            localname = str(localname).lower()
            self.unknown_endtag(localname)

        def error(self, exc):
            self.bozo = 1
            self.exc = exc
            
        def fatalError(self, exc):
            self.error(exc)
            raise exc

# TODO this is mostly copy pasted from _LooseFeedParser, should be a friendlier base class
class _LooseXSPFParser(_XSPFParserMixin, _BaseHTMLProcessor):
    def __init__(self, baseuri, baselang, encoding):
        sgmllib.SGMLParser.__init__(self)
        _XSPFParserMixin.__init__(self, baseuri, baselang, encoding) # changed

    def decodeEntities(self, element, data):
        data = data.replace('&#60;', '&lt;')
        data = data.replace('&#x3c;', '&lt;')
        data = data.replace('&#62;', '&gt;')
        data = data.replace('&#x3e;', '&gt;')
        data = data.replace('&#38;', '&amp;')
        data = data.replace('&#x26;', '&amp;')
        data = data.replace('&#34;', '&quot;')
        data = data.replace('&#x22;', '&quot;')
        data = data.replace('&#39;', '&apos;')
        data = data.replace('&#x27;', '&apos;')
        if self.contentparams.has_key('type') and not self.contentparams.get('type', 'xml').endswith('xml'):
            data = data.replace('&lt;', '<')
            data = data.replace('&gt;', '>')
            data = data.replace('&amp;', '&')
            data = data.replace('&quot;', '"')
            data = data.replace('&apos;', "'")
        return data

# TODO, patch feedparser to use this as the base stripper
def _stripDoctype(data):
    '''Strips DOCTYPE from XML document, returns stripped_data)

    stripped_data is the same XML document, minus the DOCTYPE
    '''
    entity_pattern = re.compile(r'<!ENTITY([^>]*?)>', re.MULTILINE)
    data = entity_pattern.sub('', data)
    doctype_pattern = re.compile(r'<!DOCTYPE([^>]*?)>', re.MULTILINE)
    doctype_results = doctype_pattern.findall(data)
    doctype = doctype_results and doctype_results[0] or ''
    data = doctype_pattern.sub('', data)
    return doctype, data

# TODO, make feedparser's parse method more modular
def parse(url_file_stream_or_string, etag=None, modified=None, agent=None, referrer=None, handlers=[]):
    '''Parse a XSPF from a URL, file, stream, or string'''
    result = FeedParserDict()
    result['playlist'] = FeedParserDict()
    if _XML_AVAILABLE:
        result['bozo'] = 0
    if type(handlers) == types.InstanceType:
        handlers = [handlers]
    try:
        f = _open_resource(url_file_stream_or_string, etag, modified, agent, referrer, handlers)
        data = f.read()
    except Exception, e:
        result['bozo'] = 1
        result['bozo_exception'] = e
        data = ''
        f = None

    # if feed is gzip-compressed, decompress it
    if f and data and hasattr(f, 'headers'):
        if gzip and f.headers.get('content-encoding', '') == 'gzip':
            try:
                data = gzip.GzipFile(fileobj=_StringIO(data)).read()
            except Exception, e:
                # Some feeds claim to be gzipped but they're not, so
                # we get garbage.  Ideally, we should re-request the
                # feed without the 'Accept-encoding: gzip' header,
                # but we don't.
                result['bozo'] = 1
                result['bozo_exception'] = e
                data = ''
        elif zlib and f.headers.get('content-encoding', '') == 'deflate':
            try:
                data = zlib.decompress(data, -zlib.MAX_WBITS)
            except Exception, e:
                result['bozo'] = 1
                result['bozo_exception'] = e
                data = ''

    # save HTTP headers
    if hasattr(f, 'info'):
        info = f.info()
        result['etag'] = info.getheader('ETag')
        last_modified = info.getheader('Last-Modified')
        if last_modified:
            result['modified'] = _parse_date(last_modified)
    if hasattr(f, 'url'):
        result['href'] = f.url
        result['status'] = 200
    if hasattr(f, 'status'):
        result['status'] = f.status
    if hasattr(f, 'headers'):
        result['headers'] = f.headers.dict
    if hasattr(f, 'close'):
        f.close()

    # there are four encodings to keep track of:
    # - http_encoding is the encoding declared in the Content-Type HTTP header
    # - xml_encoding is the encoding declared in the <?xml declaration
    # - sniffed_encoding is the encoding sniffed from the first 4 bytes of the XML data
    # - result['encoding'] is the actual encoding, as per RFC 3023 and a variety of other conflicting specifications
    http_headers = result.get('headers', {})
    result['encoding'], http_encoding, xml_encoding, sniffed_xml_encoding, acceptable_content_type = \
        _getCharacterEncoding(http_headers, data)
    if http_headers and (not acceptable_content_type):
        if http_headers.has_key('content-type'):
            bozo_message = '%s is not an XML media type' % http_headers['content-type']
        else:
            bozo_message = 'no Content-type specified'
        result['bozo'] = 1
        result['bozo_exception'] = NonXMLContentType(bozo_message)
        
    doctype, data = _stripDoctype(data) # changed

    baseuri = http_headers.get('content-location', result.get('href'))
    baselang = http_headers.get('content-language', None)

    # if server sent 304, we're done
    if result.get('status', 0) == 304:
        result['version'] = ''
        result['debug_message'] = 'The XSPF has not changed since you last checked, ' + \
            'so the server sent no data.  This is a feature, not a bug!'
        return result

    # if there was a problem downloading, we're done
    if not data:
        return result

    # determine character encoding
    use_strict_parser = 0
    known_encoding = 0
    tried_encodings = []
    # try: HTTP encoding, declared XML encoding, encoding sniffed from BOM
    for proposed_encoding in (result['encoding'], xml_encoding, sniffed_xml_encoding):
        if not proposed_encoding: continue
        if proposed_encoding in tried_encodings: continue
        tried_encodings.append(proposed_encoding)
        try:
            data = _toUTF8(data, proposed_encoding)
            known_encoding = use_strict_parser = 1
            break
        except:
            pass
    # if no luck and we have auto-detection library, try that
    if (not known_encoding) and chardet:
        try:
            proposed_encoding = chardet.detect(data)['encoding']
            if proposed_encoding and (proposed_encoding not in tried_encodings):
                tried_encodings.append(proposed_encoding)
                data = _toUTF8(data, proposed_encoding)
                known_encoding = use_strict_parser = 1
        except:
            pass
    # if still no luck and we haven't tried utf-8 yet, try that
    if (not known_encoding) and ('utf-8' not in tried_encodings):
        try:
            proposed_encoding = 'utf-8'
            tried_encodings.append(proposed_encoding)
            data = _toUTF8(data, proposed_encoding)
            known_encoding = use_strict_parser = 1
        except:
            pass
    # if still no luck and we haven't tried windows-1252 yet, try that
    if (not known_encoding) and ('windows-1252' not in tried_encodings):
        try:
            proposed_encoding = 'windows-1252'
            tried_encodings.append(proposed_encoding)
            data = _toUTF8(data, proposed_encoding)
            known_encoding = use_strict_parser = 1
        except:
            pass
    # if still no luck, give up
    if not known_encoding:
        result['bozo'] = 1
        result['bozo_exception'] = CharacterEncodingUnknown( \
            'document encoding unknown, I tried ' + \
            '%s, %s, utf-8, and windows-1252 but nothing worked' % \
            (result['encoding'], xml_encoding))
        result['encoding'] = ''
    elif proposed_encoding != result['encoding']:
        result['bozo'] = 1
        result['bozo_exception'] = CharacterEncodingOverride( \
            'documented declared as %s, but parsed as %s' % \
            (result['encoding'], proposed_encoding))
        result['encoding'] = proposed_encoding

    if not _XML_AVAILABLE:
        use_strict_parser = 0
    if use_strict_parser:
        # initialize the SAX parser
        xspfparser = _StrictXSPFParser(baseuri, baselang, 'utf-8') # changed
        saxparser = xml.sax.make_parser(PREFERRED_XML_PARSERS)
        saxparser.setFeature(xml.sax.handler.feature_namespaces, 1)
        saxparser.setContentHandler(xspfparser) # changed
        saxparser.setErrorHandler(xspfparser) # changed
        source = xml.sax.xmlreader.InputSource()
        source.setByteStream(_StringIO(data))
        if hasattr(saxparser, '_ns_stack'):
            # work around bug in built-in SAX parser (doesn't recognize xml: namespace)
            # PyXML doesn't have this problem, and it doesn't have _ns_stack either
            saxparser._ns_stack.append({'http://www.w3.org/XML/1998/namespace':'xml'})
        try:
            saxparser.parse(source)
        except Exception, e:
            if _debug:
                import traceback
                traceback.print_stack()
                traceback.print_exc()
                sys.stderr.write('xml parsing failed\n')
            result['bozo'] = 1
            result['bozo_exception'] = xspfparser.exc or e # changed
            use_strict_parser = 0
    if not use_strict_parser:
        xspfparser = _LooseXSPFParser(baseuri, baselang, known_encoding and 'utf-8' or '') # changed
        xspfparser.feed(data) # changed
    result['playlist'] = xspfparser.playlistdata # changed
    result['playlist']['track'] = xspfparser.tracks # changed
    result['playlist']['version'] = xspfparser.version # changed
    result['namespaces'] = xspfparser.namespacesInUse
    return result

if __name__ == '__main__':
    if not sys.argv[1:]:
        print __doc__
        sys.exit(0)
    else:
        urls = sys.argv[1:]
    zopeCompatibilityHack()
    from pprint import pprint
    for url in urls:
        print url
        print
        result = parse(url)
        pprint(result)
        print
