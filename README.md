
# Helios
Multi-threaded open-source web application security scanner

The current version can detect the following vulnerabilities:
- SQL-Injections
    - Error Based
    - Boolean Based
    - Time Based
- Cross-Site-Scripting
    - Reflected
    - Stored
- File-inclusion
    - Local file inclusion
    - Remote file inclusion
- File uploads
- Command Injection
- Backup-files
- Generic error disclosure
- Source code disclosure
- Web application fingerprint
- CMS Vulerability scanner for:
    - WordPress
    - Drupal
    - Joomla
    - Typo3
    - Textpattern
    - Magento
    - Subrion
    - CMS made simple
    - Concrete5
    - MODX Revolution
- Automatic launching of Metasploit modules (through msfrpc)
    - unsafe at the moment


# How to install
The recommended way
```
pip install Helios-Scanner
helios-update-db
helios -h
```

The manual way
```
git clone https://github.com/stefan2200/Helios.git
cd Helios
pip setup.py install

helios-update-db
helios -h
```
Please grab a coffee when the CVE database is updating, it might take a while

# How to use (Command Line)
```
usage: helios: args [-h] [-u URL] [--urls URLS]
                                 [--user-agent USER_AGENT] [-a] [-o OUTFILE]
                                 [-d] [--driver-path DRIVER_PATH]
                                 [--show-driver] [--interactive] [--no-proxy]
                                 [--proxy-port PROXY_PORT] [-c]
                                 [--max-urls MAXURLS] [--scopes SCOPES]
                                 [--scope-options SCOPE_OPTIONS] [-s] [--adv]
                                 [--cms] [--webapp] [--optimize]
                                 [--options CUSTOM_OPTIONS]
                                 [--login LOGIN_TYPE]
                                 [--login-creds LOGIN_CREDS]
                                 [--login-url LOGIN_URL]
                                 [--login-data LOGIN_DATA]
                                 [--token-url TOKEN_URL]
                                 [--header LOGIN_HEADER] [--threads THREADS]
                                 [--sslverify] [--database DB] [-v] [--msf]
                                 [--msf-host MSF_HOST] [--msf-port MSF_PORT]
                                 [--msf-creds MSF_CREDS]
                                 [--msf-endpoint MSF_URI]
                                 [--msf-nossl MSF_NOSSL] [--msf-start]

optional arguments:
  -h, --help            show this help message and exit
  -u URL, --url URL     URL to start with
  --urls URLS           file with URL's to start with
  --user-agent USER_AGENT
                        Set the user agent
  -a, --all             Run everything
  -o OUTFILE, --output OUTFILE
                        Output file to write to (JSON)

Chromedriver Options:
  -d, --driver          Run WebDriver for advanced discovery
  --driver-path DRIVER_PATH
                        Set custom path for the WebDriver
  --show-driver         Show the WebDriver window
  --interactive         Dont close the WebDriver window until keypress
  --no-proxy            Disable the proxy module for the WebDriver
  --proxy-port PROXY_PORT
                        Set a custom port for the proxy module, default: 3333

Crawler Options:
  -c, --crawler         Enable the crawler
  --max-urls MAXURLS    Set max urls for the crawler
  --scopes SCOPES       Extra allowed scopes, comma separated hostnames (* can
                        be used as wildcard)
  --scope-options SCOPE_OPTIONS
                        Various scope options (additional info in wiki)
  --wordlist WL_FILE    Additional web discovery wordlist
  --wordlist-ext WL_EXT
                        Additional comma separated web discovery extensions
                        (requires wordlist)
  --wordlist-404 WL_404
                        Custom 404 text pattern (default: use status code)
  --wordlist-status-codes WL_CODES
                        Custom comma separated found status codes

Scanner Options:
  -s, --scan            Enable the scanner
  --adv                 Enable the advanced scripts
  --cms                 Enable the CMS module
  --webapp              Enable scanning of web application frameworks like
                        Tomcat / Jboss
  --optimize            Optimize the Scanner engine (uses more resources)
  --options CUSTOM_OPTIONS
                        Comma separated list of scan options (discovery,
                        passive, injection, dangerous, all)

Login Options:
  --login LOGIN_TYPE    Set login method: basic, form, form-csrf, header
  --login-creds LOGIN_CREDS
                        Basic Auth credentials username:password
  --login-url LOGIN_URL
                        Set the URL to post to (forms)
  --login-data LOGIN_DATA
                        Set urlencoded login data (forms)
  --token-url TOKEN_URL
                        Get CSRF tokens from this page (default login-url)
  --header LOGIN_HEADER
                        Set this header on all requests (OAuth tokens etc..)
                        example: "Key: Bearer {token}"

Advanced Options:
  --threads THREADS     Set a custom number of crawling / scanning threads
  --sslverify           Enable SSL verification (requests will fail without
                        proper cert)
  --database DB         The SQLite database to use
  -v, --verbose         Show verbose stuff

Metasploit Options:
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




Crawl and scan an entire domain
helios.py -u "http://example.com/" -c -s

Safe scan
helios.py -u "http://example.com/" -c -s --options "passive,discovery" --adv

Full scan (with unsafe scripts)
helios.py -u "http://example.com/" -a --options all --max-urls 1000

Scan a single URL
helios.py -u "http://example.com/vuln.php?id=1" -s

Scan webapps and CMS systems
helios.py -u "http://example.com/blog/" --webapp --cms

Pwn a web server
helios.py -u "http://example.com/" --msf
```

Helios is built for authorized use only!
