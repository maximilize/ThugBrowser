#!/usr/bin/env python
#
# DFT.py
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA  02111-1307  USA

import os
import logging
import PyV8
import jsbeautifier
from cssutils.parse import CSSParser

try:
    from . import Window
except ImportError:
    import Window

from .W3C import *
from .W3C.DOMImplementation import DOMImplementation
from .W3C.Events.Event import Event
from .W3C.Events.MouseEvent import MouseEvent
from .W3C.Events.HTMLEvent import HTMLEvent

log        = logging.getLogger("Thug")
    
class DFT(object):
    javascript     = ('javascript', )
    vbscript       = ('vbs', 'vbscript', 'visualbasic')

    # Some event types are directed at the browser as a whole, rather than at 
    # any particular document element. In JavaScript, handlers for these events 
    # are registered on the Window object. In HTML, we place them on the <body>
    # tag, but the browser registers them on the Window. The following is the
    # complete list of such event handlers as defined by the draft HTML5 
    # specification:
    #
    # onafterprint      onfocus         ononline        onresize
    # onbeforeprint     onhashchange    onpagehide      onstorage
    # onbeforeunload    onload          onpageshow      onundo
    # onblur            onmessage       onpopstate      onunload
    # onerror           onoffline       onredo
    window_events = ('afterprint',
                     'beforeprint',
                     'beforeunload',
                     'blur',
                     'error',
                     'focus',
                     'hashchange',
                     'load',
                     'message',
                     'offline',
                     'online',
                     'pagehide',
                     'pageshow',
                     'popstate',
                     'redo',
                     'resize',
                     'storage',
                     'undo',
                     'unload')

    window_on_events = ['on' + e for e in window_events]

    def __init__(self, window):
        self.window            = window
        self.window.doc.DFT    = self
        self.anchors           = list()
        self.meta              = dict()
        self._context          = None
        log.DFT                = self
        self._init_events()
   
    def _init_events(self):
        self.listeners = list()

        # Events are handled in the same order they are inserted in this list
        self.handled_events = ['load', 'mousemove']

        for event in log.ThugOpts.events:
            self.handled_events.append(event)

        log.debug("Handling DOM Events: %s" % (",".join(self.handled_events), ))
        self.handled_on_events = ['on' + e for e in self.handled_events]
        self.dispatched_events = set()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass

    @property
    def context(self):
        if self._context is None:
            self._context = self.window.context

        return self._context

    def shift(self, script, s):
        if script.lower().startswith(s):
            return script[len(s):].lstrip()
        return script

    def fix(self, script):
        script = self.shift(script, 'javascript:')
        script = self.shift(script, 'return')
        return script

    def get_evtObject(self, elem, evtType):
        evtObject = None

        if evtType in MouseEvent.MouseEventTypes:
            evtObject = MouseEvent(evtType, elem)

        if evtType in HTMLEvent.HTMLEventTypes:
            evtObject = HTMLEvent(evtType, elem)

        if evtObject is None:
            return None

        evtObject.eventPhase = Event.AT_TARGET
        evtObject.currentTarget = elem
        return evtObject

    # Events handling
    def handle_element_event(self, evt):
        for (elem, eventType, listener, capture) in self.listeners:
            if getattr(elem, 'name', None) is None:
                continue

            if elem.name in ('body', ):
                continue

            if eventType in (evt, ):
                if (elem._node, evt) in self.dispatched_events:
                    continue
            
                elem._node.dispatchEvent(evt)
                self.dispatched_events.add((elem._node, evt))

    def handle_window_event(self, onevt):
        if onevt in self.handled_on_events:
            handler = getattr(self.window, onevt, None)
            if handler:
                evtObject = self.get_evtObject(self.window, onevt[2:])
                if log.ThugOpts.Personality.isIE() and log.ThugOpts.Personality.browserVersion < '9.0':
                    self.window.event = evtObject
                    handler()
                else:
                    handler(evtObject)

    def handle_document_event(self, onevt):
        if onevt in self.handled_on_events:
            handler = getattr(self.window.doc, onevt, None)
            if handler:
                evtObject = self.get_evtObject(self.window.doc, onevt[2:])
                if log.ThugOpts.Personality.isIE() and log.ThugOpts.Personality.browserVersion < '9.0':
                    self.window.event = evtObject
                    handler()
                else:
                    handler(evtObject)

        #if not getattr(self.window.doc.tag, '_listeners', None):
        #    return

        if not '_listeners' in self.window.doc.tag.__dict__:
            return

        for (eventType, listener, capture) in self.window.doc.tag._listeners:
            if not eventType in (onevt[2:], ):
                continue
                
            evtObject = self.get_evtObject(self.window.doc, eventType)
            if log.ThugOpts.Personality.isIE() and log.ThugOpts.Personality.browserVersion < '9.0':
                self.window.event = evtObject
                listener()
            else:
                listener(evtObject)

    def build_event_handler(self, ctx, h):
        # When an event handler is registered by setting an HTML attribute
        # the browser converts the string of JavaScript code into a function.
        # Browsers other than IE construct a function with a single argument
        # named `event'. IE constructs a function that expects no argument.
        # If the identifier `event' is used in such a function, it refers to
        # `window.event'. In either case, HTML event handlers can refer to 
        # the event object as `event'.
        if log.ThugOpts.Personality.isIE():
            return ctx.eval("(function() { with(document) { with(this.form || {}) { with(this) { event = window.event; %s } } } }) " % (h, ))

        return ctx.eval("(function(event) { with(document) { with(this.form || {}) { with(this) { %s } } } }) " % (h, ))

    def set_event_handler_attributes(self, elem):
        try:
            attrs = elem.attrs
        except:
            return
       
        if 'language' in list(attrs.keys()) and not attrs['language'].lower() in ('javascript', ):
            return

        for evt, h in attrs.items():
            if evt not in self.handled_on_events:
                continue

            self.attach_event(elem, evt, h)

    def attach_event(self, elem, evt, h):
        handler = None

        if isinstance(h, basestring):
            handler = self.build_event_handler(self.context, h)
            PyV8.JSEngine.collect()
        elif isinstance(h, PyV8.JSFunction):
            handler = h
        else:
            try:
                handler = getattr(self.context.locals, h, None)
            except:
                pass

        if not handler:
            return

        if getattr(elem, 'name', None) and elem.name in ('body', ) and evt in self.window_on_events:
            setattr(self.window, evt, handler)
            return

        if not getattr(elem, '_node', None):
            DOMImplementation.createHTMLElement(self.window.doc, elem)
            
        elem._node._attachEvent(evt, handler, True)

    def set_event_listeners(self, elem):
        p = getattr(elem, '_node', None)

        if p:
            for evt in self.handled_on_events:
                h = getattr(p, evt, None)
                if h:
                    self.attach_event(elem, evt, h)
            
        listeners = getattr(elem, '_listeners', None)
        if listeners:
            for (eventType, listener, capture) in listeners:
                if eventType in self.handled_events:
                    self.listeners.append((elem, eventType, listener, capture))

    @property
    def javaUserAgent(self):
        javaplugin = log.ThugVulnModules._javaplugin.split('.')
        last = javaplugin.pop()
        version =  '%s_%s' % ('.'.join(javaplugin), last)
        return log.ThugOpts.Personality.javaUserAgent % (version, )

    def do_handle_params(self, object):
        params = dict()

        for child in object.find_all():
            name = getattr(child, 'name', None)
            if name is None:
                continue

            if name.lower() in ('param', ):
                if all(p in child.attrs for p in ('name', 'value', )):
                    params[child.attrs['name'].lower()] = child.attrs['value']

            if name.lower() in ('embed', ):
                self.handle_embed(child)

        if not params:
            return

        headers = dict()
        headers['Connection'] = 'keep-alive'

        if 'type' in params:
            headers['Content-Type'] = params['type']
        else:
            name = getattr(object, 'name', None)

            if name in ('applet', ):
                headers['Content-Type'] = 'application/x-java-archive'

        if 'Content-Type' in headers and 'java' in headers['Content-Type'] and log.ThugOpts.Personality.javaUserAgent:
            headers['User-Agent'] = self.javaUserAgent

        for key in ('filename', 'movie', ):
            if not key in params:
                continue

            try:
                self.window._navigator.fetch(params[key], headers = headers, redirect_type = "params")
            except:
                pass

        if not 'archive' in params and not 'code' in params:
            return

        if 'codebase' in params:
            archive = "%s%s" % (params['codebase'], params['archive'])
        else:
            archive = params['archive']

        try:
            self.window._navigator.fetch(archive, headers = headers, redirect_type = "params")
        except:
            pass

        #if 'codebase' in params:
        #    code = "%s%s" % (params['codebase'], params['code'])
        #else:
        #    code = params['code']

        #try:
        #    self.window._navigator.fetch(code, headers = headers)
        #except:
        #    pass

    def _get_script_for_event_params(self, attr_event):
        params = attr_event.split('(')
        if len(params) < 2:
            return None

        params = params[1].split(')')[0]
        return params.split(',')

    def _handle_script_for_event(self, script):
        attr_for   = script.get("for", None)
        attr_event = script.get("event", None)

        if not attr_for or not attr_event:
            return

        params = self._get_script_for_event_params(attr_event)
        if not params:
            return

        if 'playstatechange' in attr_event.lower():
            with self.context as ctx:
                newState = params.pop()
                ctx.eval("%s = 0;" % (newState.strip(), ))
                try:
                    oldState = params.pop()
                    ctx.eval("%s = 3;" % (oldState.strip(), ))
                except:
                    pass

    def handle_script(self, script):
        language = script.get('language', 'javascript').lower()
        if 'javascript' in language:
            language = 'javascript'

        handler = getattr(self, "handle_%s" % (language, ), None)

        if not handler:
            log.warning("Unhandled script language: %s" % (language, ))
            return

        if log.ThugOpts.Personality.isIE():
            self._handle_script_for_event(script)

        handler(script)

    def handle_javascript(self, script):
        try:
            log.info(jsbeautifier.beautify(str(script)))
        except:
            log.info(script)

        src = script.get('src', None)
        if src is not None:
            try:
                response, js = self.window._navigator.fetch(src, redirect_type = "script src")
            except:
                return

            if response.status == 404:
                return
        else:
            js = getattr(script, 'text', None)

        if js:
            self.window.evalScript(js, tag=script)

    def handle_noscript(self, script):
        pass

    def handle_embed(self, embed):
        log.warning(embed)

        src = embed.get('src', None)
        if src is None:
            return

        headers = dict()

        embed_type = embed.get('type', None)
        if embed_type:
            headers['Content-Type'] = embed_type

        try:
            self.window._navigator.fetch(src, headers = headers, redirect_type = "embed")
        except:
            pass

    def handle_meta(self, meta):
        return
        log.info(meta)

        name = meta.get('name', None)
        if name and name.lower() in ('generator', ):
            content = meta.get('content', None)

        http_equiv = meta.get('http-equiv', None)
        if not http_equiv or http_equiv.lower() != 'refresh':
            return

        content = meta.get('content', None)
        if not content or not 'url' in content.lower():
            return

        timeout = 0
        url     = None

        for s in content.split(';'):
            s = s.strip()
            if s.lower().startswith('url='):
                url = s[4:]
            try:
                timeout = int(s)
            except:
                pass

        if not url:
            return

        if url.startswith("'") and url.endswith("'"):
            url = url[1:-1]

        if url in self.meta and self.meta[url] >= 3:
            return

        try:
            response, content = self.window._navigator.fetch(url, redirect_type = "meta")
        except:
            return

        if response.status == 404:
            return

        if url in self.meta:
            self.meta[url] += 1
        else:
            self.meta[url] = 1

        #self.window.doc     = w3c.parseString(content)
        #self.window.doc.DFT = self
        #self.window.open(url)
        #self.run()

        doc    = w3c.parseString(content)
        window = Window.Window(self.window.url, doc, personality = log.ThugOpts.useragent)
        window.open(url)

        dft = DFT(window)
        dft.run()

    def handle_frame(self, frame, redirect_type = 'frame'):
        return
        log.warning(frame)
        
        src = frame.get('src', None)
        if not src:
            return 

        try:
            response, content = self.window._navigator.fetch(src, redirect_type = redirect_type)
        except:
            return

        if response.status == 404:
            return

        if 'content-type' in response:
            handler = log.MIMEHandler.get_handler(response['content-type'])
            if handler and handler(content):
                return

        _src = self.window._navigator._normalize_url(src)
        if _src:
            src = _src

        doc    = w3c.parseString(content)
        window = Window.Window(self.window.url, doc, personality = log.ThugOpts.useragent)
        window.open(src)

        dft = DFT(window)
        dft.run()

    def handle_body(self, body):
        pass

    def do_handle_font_face_rule(self, rule):
        for p in rule.style:
            if p.name.lower() not in ('src', ):
                continue

            url = p.value
            if url.startswith('url(') and len(url) > 4:
                url = url.split('url(')[1].split(')')[0]

            try:
                self.window._navigator.fetch(url, redirect_type = "font face")
            except:
                return

    def handle_style(self, style):
        return
        log.info(style)

        cssparser = CSSParser(loglevel = logging.CRITICAL, validate = False)

        try:
            sheet = cssparser.parseString(style.text)
        except:
            return

        for rule in sheet:
            if rule.type == rule.FONT_FACE_RULE:
                self.do_handle_font_face_rule(rule)

    def follow_href(self, href):
        doc    = w3c.parseString('')
        window = Window.Window(self.window.url, doc, personality = log.ThugOpts.useragent)
        window = window.open(href)
            
        if window:
            dft = DFT(window)
            dft.run()

    def do_handle(self, child, skip=True):
        name = getattr(child, "name", None)

        if name is None:
            return False

        if skip and name in ('object', 'applet', ):
            return False

        handler = getattr(self, "handle_%s" % (str(name.lower()), ), None)
        if handler:
            handler(child)
            return True

        return False

    def _run(self, soup = None):
        log.debug(self.window.doc)
        
        if soup is None:
            soup = self.window.doc.doc
    
        _soup = soup

        for child in soup.descendants:
            self.set_event_handler_attributes(child)
            if not self.do_handle(child):
                continue

            if tuple(soup.descendants) == tuple(_soup.descendants):
                continue
            
            for _child in set(soup.descendants) - set(_soup.descendants): 
                name = getattr(_child, "name", None)
                if name:
                    self.do_handle(_child, False)
            
            _soup = soup

        for child in soup.descendants:
            self.set_event_listeners(child)

        for evt in self.handled_on_events:
            try:
                self.handle_window_event(evt)
            except:
                log.warning("[handle_window_event] Event %s not properly handled" % (evt, ))

        for evt in self.handled_on_events:
            try:
                self.handle_document_event(evt)
            except:
                log.warning("[handle_document_event] Event %s not properly handled" % (evt, ))

        for evt in self.handled_events:
            try:
                self.handle_element_event(evt)
            except:
                log.warning("[handle_element_event] Event %s not properly handled" % (evt, ))

    def run(self):
        with self.context:
            self._run()
