#!/usr/bin/env python
# -*- coding: utf-8 -*-


# This will start the helios framework

import argparse
import sys

import helios


def main():
    usage = """%s: args""" % sys.argv[0]
    parser = argparse.ArgumentParser(usage)
    parser.add_argument('-u', '--url', help='URL to start with', dest='url', default=None)
    parser.add_argument('--urls', help='file with URL\'s to start with', dest='urls', default=None)
    parser.add_argument('--user-agent', help='Set the user agent', dest='user_agent', default=None)
    parser.add_argument('-a', '--all', help='Run everything', dest='allin', default=None, action='store_true')
    parser.add_argument('-o', '--output', help='Output file to write to (JSON)', dest='outfile', default=None)

    group_driver = parser.add_argument_group(title="Chromedriver Options")
    group_driver.add_argument('-d', '--driver', help='Run WebDriver for advanced discovery',
                              dest='driver', action='store_true')
    group_driver.add_argument('--driver-path', help='Set custom path for the WebDriver', dest='driver_path',
                              default=None)
    group_driver.add_argument('--show-driver', help='Show the WebDriver window', dest='show_driver',
                              default=None, action='store_true')
    group_driver.add_argument('--interactive', help='Dont close the WebDriver window until keypress',
                              dest='interactive', default=False, action='store_true')
    group_driver.add_argument('--no-proxy', help='Disable the proxy module for the WebDriver', dest='proxy',
                              action='store_false', default=True)
    group_driver.add_argument('--proxy-port', help='Set a custom port for the proxy module, default: 3333',
                              dest='proxy_port', default=None)

    group_crawler = parser.add_argument_group(title="Crawler Options")
    group_crawler.add_argument('-c', '--crawler', help='Enable the crawler', dest='use_crawler', action='store_true')
    group_crawler.add_argument('--max-urls', help='Set max urls for the crawler', dest='maxurls', default=200)
    group_crawler.add_argument('--scopes',
                               help='Extra allowed scopes, comma separated hostnames (* can be used to wildcard)',
                               dest='scopes', default=None)
    group_crawler.add_argument('--scope-options', help='Various scope options',
                               dest='scope_options', default=None)

    group_crawler.add_argument('--wordlist', help='Additional web discovery wordlist',
                               dest='wl_file', default=None)
    group_crawler.add_argument('--wordlist-ext',
                               help='Additional comma separated web discovery extensions (requires wordlist)',
                               dest='wl_ext', default=None)
    group_crawler.add_argument('--wordlist-404', help='Custom 404 text pattern (default: use status code)',
                               dest='wl_404', default=None)
    group_crawler.add_argument('--wordlist-status-codes', help='Custom comma separated found status codes',
                               dest='wl_codes', default=None)

    group_scanner = parser.add_argument_group(title="Scanner Options")
    group_scanner.add_argument('-s', '--scan', help='Enable the scanner', dest='scanner',
                               default=False, action='store_true')
    group_scanner.add_argument('--adv', help='Enable the advanced scripts', dest='use_adv_scripts',
                               default=False, action='store_true')
    group_scanner.add_argument('--cms', help='Enable the CMS module', dest='cms_enabled',
                               action='store_true', default=False)
    group_scanner.add_argument('--webapp', help='Enable scanning of web application frameworks like Tomcat / Jboss',
                               dest='webapp_enabled', action='store_true', default=False)
    group_scanner.add_argument('--optimize', help='Optimize the Scanner engine (uses more resources)', dest='optimize',
                               action='store_true', default=False)
    group_scanner.add_argument('--options',
                               help='Comma separated list of scan options '
                                    '(discovery, passive, injection, dangerous, all)',
                               dest='custom_options', default=None)

    group_login = parser.add_argument_group(title="Login Options")
    group_login.add_argument('--login', help='Set login method: basic, form, form-csrf, header',
                             dest='login_type', default=None)
    group_login.add_argument('--login-creds', help='Basic Auth credentials username:password',
                             dest='login_creds', default=None)
    group_login.add_argument('--login-url', help='Set the URL to post to (forms)', dest='login_url', default=None)
    group_login.add_argument('--login-data', help='Set urlencoded login data (forms)',
                             dest='login_data', default=None)
    group_login.add_argument('--token-url', help='Get CSRF tokens from this page (default login-url)',
                             dest='token_url', default=None)
    group_login.add_argument('--header', help='Set this header on all requests (OAuth tokens etc..) '
                                              'example: "Key: Bearer {token}"',
                             dest='login_header', default=None, action="append")

    group_adv = parser.add_argument_group(title="Advanced Options")
    group_adv.add_argument('--threads', help='Set a custom number of crawling / scanning threads', dest='threads',
                           default=None)
    group_adv.add_argument('--sslverify', default=False, action="store_true", dest="sslverify",
                           help="Enable SSL verification (requests will fail without proper cert)")

    group_adv.add_argument('--database', help='The SQLite database to use', dest='db', default="helios.db")
    group_adv.add_argument('-v', '--verbose', dest="verbose", default=False, action="store_true",
                           help="Show verbose stuff")

    group_msf = parser.add_argument_group(title="Metasploit Options")
    group_msf.add_argument('--msf', help='Enable the msfrpcd exploit module', dest='msf', default=False,
                           action='store_true')
    group_msf.add_argument('--msf-host', help='Set the msfrpcd host', dest='msf_host', default="localhost")
    group_msf.add_argument('--msf-port', help='Set the msfrpcd port', dest='msf_port', default="55553")
    group_msf.add_argument('--msf-creds', help='Set the msfrpcd username:password',
                           dest='msf_creds', default="msf:msfrpcd")
    group_msf.add_argument('--msf-endpoint', help='Set a custom endpoint URI', dest='msf_uri', default="/api/")
    group_msf.add_argument('--msf-nossl', help='Disable SSL', dest='msf_nossl', default=False)
    group_msf.add_argument('--msf-start', help='Start msfrpcd if not running already',
                           dest='msf_autostart', default=False, action='store_true')

    opts = parser.parse_args(sys.argv[1:])
    urls = []
    if not opts.url:
        if not opts.urls:
            print("-u or --urls is required to start")
            sys.exit(1)
        else:
            with open(opts.urls, 'r') as urlfile:
                urls = [x.strip() for x in urlfile.read().strip().split('\n')]
                print("Got %d start URL's from file %s" % (len(urls), opts.urls))
    else:
        urls = [opts.url]

    instance = helios.Helios(opts)
    try:
        instance.run(urls, opts.scopes)
    except KeyboardInterrupt:
        instance.logger.warning("KeyboardInterrupt received, shutting down")
        instance.db.end()
    except Exception as e:
        if instance.options.verbose:
            instance.db.end()
            raise
        instance.logger.error(str(e))
        instance.logger.warning("Critical error received, shutting down")
        instance.db.end()


if __name__ == "__main__":
    main()
