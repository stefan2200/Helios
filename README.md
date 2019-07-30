
# Helios
Multi-threaded open-source web application security scanner

## Supports Python 2.x and Python 3.x

The current version can detect the following vulnerabilities:
- SQL-Injections
    - Error Based
    - Boolean Based
    - Time Based
- Cross-Site-Scripting
    - Reflected
    - Stored
- File-inclusion
    - Local file inclusion (readfile)
    - Remote file inclusion (using api.myip.com)
- Command Injection
    - Windows + Unix + OSX
- Backup-files
- Generic error disclosure
- Source code disclosure
- Web application fingerprint
- CMS Vulns
    - WordPress (advanced)
    - Drupal (basic)
    - Joomla (basic)
- Automatic launching of Metasploit modules (through msfrpc)
    

# Features
- Uses multi-threading (very very fast)
- Processes AJAX/XHR requests
- Widely adaptable


# How to install
```
git clone https://github.com/stefan2200/Helios.git
pip install -r requirements.txt
python helios.py -h
```

# How to use (Command Line)
```
helios.py: -u URL args

optional arguments:
  -h, --help            show this help message and exit
  -u URL, --url URL     URL to start with
  --user-agent USER_AGENT
                        Set the user agent
  -c, --crawl           Enable the crawler
  -d, --driver          Run WebDriver for advanced discovery
  --driver-path DRIVER_PATH
                        Set custom path for the WebDriver
  --show-driver         Show the WebDriver window
  --max-urls MAXURLS    Set max urls for the crawler
  -a, --all             Run everything
  --no-proxy            Disable the proxy module for the WebDriver
  --proxy-port PROXY_PORT
                        Set a custom port for the proxy module, default: 3333
  --threads THREADS     Set a custom number of crawling / scanning threads
  -s, --scan            Enable the scanner
  --adv                 Enable the advanced scripts
  -o OUTFILE, --output OUTFILE
                        Output file to write to (JSON)
  --scripts             Enable the script engine
  --options CUSTOM_OPTIONS
                        Comma separated list of scan options (discovery,
                        passive, injection, dangerous, all)
  --msf                 Enable the msfrpcd exploit module
  --msf-host MSF_HOST   Set the msfrpcd host
  --msf-port MSF_PORT   Set the msfrpcd port
  --msf-creds MSF_CREDS
                        Set the msfrpcd username:password
  --msf-endpoint MSF_URI
                        Set a custom endpoint URI
  --msf-nossl MSF_NOSSL
                        Disable SSL
  --msf-start           Start msfrpcd if not running already
  -v, --verbose         Verbose mode




Crawl and scan an entire domain
helios.py -u "http://example.com/" -c -s --scripts

Safe scan
helios.py -u "http://example.com/" -c -s --options "passive,discovery" --adv

Full scan
helios.py -u "http://example.com/" -a --driver --options all --max-urls 1000

Scan a single URL
helios.py -u "http://example.com/vuln.php?id=1" -s --scripts

Pwn a web server
helios.py -u "http://example.com/" --msf
```

# How to use (Module Crawler)
```python
from helios import Crawler
# create new crawler class
c = Crawler()
# run the crawler against the start url
c.run("https://example.com/")
# print all visited links
print(c.scraped_pages)
```

# How to use (Module Scanner)
```python
from helios import Parser
from helios import Request
# create new ScriptEngine class
s = Parser.ScriptEngine()
# create an Request object
req = Request.Request(url="https://example.com/test.php?id=1", data={'test': 'value'})
# send the initial request
req.run()
s.run_scripts(req)
# print all results
print(s.results)
```

# What is next?
- create a fully working post back crawler / scanner for ASPX/JSP type sites
- even more scripts
- better output format (somewhat done)

