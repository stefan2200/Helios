# The Helios Project
Web Application security made easy

# The purpose
This project combines various techniques to crawl, analyse and detect vulnerabilities in web applications. 
Currently the scripts work best against PHP type webapps but ASP(X), JSP and pure JavaScript will soon be introduced

# What can it do
It uses 2 ways of crawling a site: first it passively crawls and extracts links / postdata from the seen pages. 
Second it visits all pages again using a WebDriver and analyses requests with an interception proxy (the Mefjus project).

After the crawling cycle there will be 2 ways of vuln detection:
pre-defined JSON scripts and more custom modular scripts.

## beware! this current version does not support Python 3 yet!

The current version can detect the following vulnerabilities:
- (BLIND) SQL-Injections
- Cross-Site-Scripting (both reflected and stored)
- (Local/Remote) File-inclusion (various filter bypass techniques)
- Command Injection
- Backup-files
- Generic error disclosure
- Juicy files (readable .htaccess etc..)

# Why use helios?
- Super fast
- Processes AJAX/XHR requests
- Adaptable and easy to use
- Allows easy modding

# Used modules
- pymiproxy
- selenium
- requests
- filelock (to fix some of the problems that multi-threading creates)
- futures (ThreadPoolExecutor)

# How to install
```
Clone this GIT
pip install -r requirements.txt
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

![Example 2](images/Example2.PNG?raw=true "Example 2")
![Example 1](images/Example1.PNG?raw=true "Example 1")

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
- multi-threaded scanner interface
- extract even more url / post data (checkboxes, ng-elements etc..)
- more scripts
- even more scripts
- better output format
- improved logging
- managed version with dashboard.. ? maybe.. ?

# Support Python 3 will be here soon
Very very soon :)