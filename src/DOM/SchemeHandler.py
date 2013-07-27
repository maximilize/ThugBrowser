
import logging
log = logging.getLogger("Thug")

class SchemeHandler:
    def __init__(self):
        pass

    def handle_hcp(self, window, url):
        log.warning('Microsoft Internet Explorer HCP Scheme Detected')

        hcp = url.split('svr=')
        if len(hcp) < 2:
            return

        hcp = hcp[1].split('defer>')
        if len(hcp) < 2:
            return 

        hcp = hcp[1].split('</script')
        if not hcp:
            return 

        if not hcp[0]:
            return

        window.evalScript(hcp[0])
