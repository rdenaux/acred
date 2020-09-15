#
# Copyright (c) 2019 Expert System iberia
#
"""
Run acred services
"""
import logging
import argparse

logger = logging.getLogger('runsrv')

def service_port(config, srvname):
    return int(config[srvname]['port'])


def run_app(app, debug, config, port):
    try:
        # Production server in HTTPS Mode
        if config['acredapi']['https'] != '0':
            logger.info("Running app with ssl")
            context = (config['acredapi']['ssl_crt'], config['acredapi']['ssl_key'])
            app.run(host='0.0.0.0', port=port,
                    ssl_context=context, threaded=True, debug=debug)

        # Localhost-only HTTP development server
        else:
            logger.warning("HTTPS is not configured, defaulting to localhost only")
            app.run(host='0.0.0.0', debug=debug, port=port)
    except Exception as e:
        logger.error("Failed to run app?" + str(e))


if __name__ == '__main__':        
    parser = argparse.ArgumentParser(description='Run acred services', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-service', default='acredapi', help='Name of the service', required=False,
                        choices=['acredapi', 'claimencoder', 'claimneuralindex', 'worthinesschecker'])
    args = parser.parse_args()
    logger.info("Running service %s" % args.service)
    if args.service == 'acredapi':
        try:
            from acredapi import app, debug, config
            run_app(app, debug, config, service_port(config, args.service))
        except Exception as e:
            logger.error("Failed to run acredapi: " + str(e), e)
    elif args.service == 'claimencoder':
        from claimencoder import app, debug, config
        run_app(app, debug, config, service_port(config, args.service))
    elif args.service == 'claimneuralindex':
        from claimneuralindex import app, debug, config
        run_app(app, debug, config, service_port(config, args.service))
    elif args.service == 'worthinesschecker':
        from worthiness import app, debug, config
        run_app(app, debug, config, service_port(config, args.service))
    else:
        raise ValueError("Unsupported service " + service)
