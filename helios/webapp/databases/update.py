import optparse
import sys
import logging

import helios.webapp.databases.process as process

config = {
    'typo3': {
        'Typo3': 'https://www.cvedetails.com/vulnerability-list/vendor_id-3887/Typo3.html'
    },
    'tomcat': {
        'Tomcat': 'https://www.cvedetails.com/vulnerability-list/vendor_id-45/product_id-887/Apache-Tomcat.html',
        'Jboss': 'https://www.cvedetails.com/vulnerability-list/vendor_id-25/product_id-14972/Redhat-Jboss-Enterprise-Application-Platform.html'
    },
    'subrion': {
        'Subrion': 'https://www.cvedetails.com/vulnerability-list/vendor_id-9328/product_id-23428/Intelliants-Subrion-Cms.html'
    },
    'textpattern': {
        'Textpattern': 'https://www.cvedetails.com/vulnerability-list/vendor_id-5344/Textpattern.html'
    },
    'cmsmadesimple': {
        'CmsMadeSimple': 'https://www.cvedetails.com/vulnerability-list/vendor_id-3206/Cmsmadesimple.html'
    },
    'magento': {
        'Magento': 'https://www.cvedetails.com/vulnerability-list/vendor_id-15393/product_id-31613/Magento-Magento.html'
    },
    'modx_revolution': {
        'Revolution': 'https://www.cvedetails.com/vulnerability-list/vendor_id-11576/product_id-23360/Modx-Modx-Revolution.html'
    },
    'phpmyadmin': {
        'phpMyAdmin': 'https://www.cvedetails.com/vulnerability-list/vendor_id-784/Phpmyadmin.html'
    },
    'concrete5': {
        'Concrete5': 'https://www.cvedetails.com/vulnerability-list/vendor_id-11506/product_id-23747/Concrete5-Concrete5.html'
    },
    'php': {
        'PHP': 'https://www.cvedetails.com/vulnerability-list/vendor_id-74/product_id-128/PHP-PHP.html'
    }
}

def main():
    parser = optparse.OptionParser()
    parser.add_option('-m', '--module', dest="module", default=None, help="The module to update")
    parser.add_option('-a', '--all', dest="all", default=False, action="store_true", help="Update all modules")
    parser.add_option('-v', dest="verbose", default=False, action="store_true", help="Show verbose stuff")
    options, args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if options.verbose else logging.INFO)
    if options.all:
        for root in config:
            for entry in config[root]:
                print("Updating database %s_vulns.json with entries from %s" % (root, entry))
                process.CVEProcessor().run(config[root], root)

    elif options.module:
        module = options.module
        if module not in config:
            print("Unknown module %s, options are:" % module)
            for key in config:
                print(key)
            sys.exit(1)
        for entry in config[module]:
            print("Updating database %s_vulns.json with entries from %s" % (module, entry))
            process.CVEProcessor().run(config[module], module)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
