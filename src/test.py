import logging

from DOM import Window, DFT
from DOM.W3C import w3c

from DOM import MIMEHandler, SchemeHandler

from ThugAPI.ThugOpts import ThugOpts
from ThugAPI.ThugVulnModules import ThugVulnModules

consolehandler = logging.StreamHandler()
logging.getLogger().addHandler(consolehandler)
logging.getLogger().setLevel(logging.WARNING)

log = logging.getLogger("Thug")
log.ThugOpts = ThugOpts()
log.ThugVulnModules  = ThugVulnModules()
log.MIMEHandler = MIMEHandler.MIMEHandler()
log.SchemeHandler = SchemeHandler.SchemeHandler()

html = '''
<html>
    <head>
        <title>Foo Title</title>
        <script type="text/javascript" src="http://ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.js"></script>
        <ript type="text/javascript" src="http://www.download.am/assets/js/prototype.js"></ript>
    </head>
    <body>
        <div id="foo">bar</div>
        <script type="text/javascript">
            document.write("fuck");
            //$('#foo').html('mighty!');
            $('#foo').html('mighty!');
            var hasFlash = false;
            try {
              var fo = new ActiveXObject('ShockwaveFlash.ShockwaveFlash');
              if(fo) hasFlash = true;
            }catch(e){
            alert(e);
              if(navigator.mimeTypes ["application/x-shockwave-flash"] != undefined) hasFlash = true;
            }
            hasFlash;navigator.mimeTypes ["application/x-shockwave-flash"]
        </script>
        hi
    </body>
</html>
'''
log.ThugOpts.useragent = 'winxpchrome20'
doc = w3c.parseString(html)
window = Window.Window('about:blank', doc, personality=log.ThugOpts.useragent)
window = window.open('http://adf.ly/IANxN')
#window = window.open('http://streamcloud.eu/wo46kwbhow2c/Breaking.Bad.S02E11.Mandala.German.WS.DVDRiP.XviD-RSG.avi.html')

dft = DFT.DFT(window)
dft.run()
print dft
print type(window.doc)
print window.doc
