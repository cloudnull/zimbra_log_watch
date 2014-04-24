#!/usr/bin/env python
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================

"""Simple Daemon watching for DelegateAuthRequest in zimbra auth.log

request is performed on your Zimbra Server.

To use this simply start it. I would recommend using start-stop-daemon command
or the daemon command these will make the application start and stop along
with the system.
"""

import ConfigParser
import datetime
import logging
from logging import handlers
import os
import platform
import signal
import smtplib
import sys
import time

from email.mime.text import MIMEText


def logger_setup(name, debug_logging=False, handler=False):
    """Setup logging for your application

    :param name: ``str``
    :param debug_logging: ``bol``
    :param handler: ``bol``
    :return: ``object``
    """

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s:%(module)s:%(levelname)s => %(message)s"
    )

    log = logging.getLogger(name)

    fileHandler = handlers.RotatingFileHandler(
        filename=return_logfile(filename='%s.log' % name),
        maxBytes=51200000,
        backupCount=5
    )

    streamHandler = logging.StreamHandler()
    if debug_logging is True:
        log.setLevel(logging.DEBUG)
        fileHandler.setLevel(logging.DEBUG)
        streamHandler.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)
        fileHandler.setLevel(logging.INFO)
        streamHandler.setLevel(logging.INFO)

    streamHandler.setFormatter(formatter)
    fileHandler.setFormatter(formatter)

    log.addHandler(streamHandler)
    log.addHandler(fileHandler)

    if handler is True:
        return fileHandler
    else:
        return log


def return_logfile(filename):
    """Return a path for logging file.

    IF "/var/log/" does not exist, or you don't have write permissions to
    "/var/log/" the log file will be in your working directory
    Check for ROOT user if not log to working directory.

    :param filename: ``str``
    :return: ``str``
    """

    if os.path.isfile(filename):
        return filename
    else:
        user = os.getuid()
        log_loc = '/var/log'
        if not user == 0:
            logfile = filename
        else:
            try:
                logfile = '%s/%s' % (log_loc, filename)
            except Exception:
                logfile = '%s' % filename
        return logfile


def _get_time():
    """Return the current UTC Time."""
    return datetime.datetime.utcnow()


def is_int(value):
    """Return int if the value can be an int.

    :param value: ``str``
    :return: ``int`` :return: ``str``
    """
    try:
        return int(value)
    except ValueError:
        return value


class ConfigurationSetup(object):
    """Parse arguments from a Configuration file.

    Note that anything can be set as a "Section" in the argument file.
    """
    def __init__(self):
        # System configuration file
        sys_config = os.path.join('/etc', APP_NAME, '%s.ini' % APP_NAME)

        # User configuration file
        home = os.getenv('HOME')
        user_config = os.path.join(home, '.%s.ini' % APP_NAME)

        if os.path.exists(user_config):
            self.config_file = user_config
        elif os.path.exists(sys_config):
            self.config_file = sys_config
        else:
            msg = (
                'Configuration file for %s was not found. Valid'
                ' configuration files are [ %s ] or [ %s ]'
                % (APP_NAME, user_config, sys_config)
            )
            raise SystemExit(msg)

    def config_args(self, section='default'):
        """Loop through the configuration file and set all of our values.

        :param section: ``str``
        :return: ``dict``
        """
        if sys.version_info >= (2, 7, 0):
            parser = ConfigParser.SafeConfigParser(allow_no_value=True)
        else:
            parser = ConfigParser.SafeConfigParser()

        # Set to preserve Case
        parser.optionxform = str
        args = {}
        try:
            parser.read(self.config_file)
            for name, value in parser.items(section):
                name = name.encode('utf8')
                if any([value == 'False', value == 'false']):
                    value = False
                elif any([value == 'True', value == 'true']):
                    value = True
                else:
                    value = is_int(value=value)
                args[name] = value
        except Exception as exp:
            LOG.error('Failure Reading in the configuration file. %s' % exp)
            return {}
        else:
            return args


class Mailer(object):
    def __init__(self, message):
        self.msg = message

        # Set SMTP
        mail_url = APP_CONFIG.get('mail_url')
        mail_port = APP_CONFIG.get('mail_port')
        self.smtp = smtplib.SMTP(mail_url, mail_port)

        if APP_CONFIG.get('debug', False) is True:
            self.smtp.set_debuglevel(True)

        key = APP_CONFIG.get('mail_key')
        cert = APP_CONFIG.get('mail_cert')
        if key is not None and cert is not None:
            self.smtp.starttls(key, cert)
        else:
            self.smtp.starttls()

        username = APP_CONFIG.get('mail_username')
        password = APP_CONFIG.get('mail_password')
        if username and password:
            self.smtp.login(username, password)

        # Deliver Cus Messages
        self.cus_messages()

        # Stop SMTP
        self.smtp.quit()

    def cus_messages(self):
        """Generate Customer Emails."""
        try:
            customer_message = self.msg.encode('utf8')

            em_msg = MIMEText(customer_message, 'plain', None)
            em_msg["Subject"] = "DelegateAuthRequest on %s" % HOSTNAME
            em_msg["From"] = APP_CONFIG.get('mail_username')
            em_msg["To"] = APP_CONFIG.get('send_to')
            em_msg["Reply-To"] = HOSTNAME

            # Send Customer Messages
            self.smtp.sendmail(
                from_addr=em_msg["From"],
                to_addrs=em_msg["To"],
                msg=em_msg.as_string()
            )
        except Exception as exp:
            LOG.error('Failed to send message due to "%s"' % exp)


class LogRead(object):
    def __init__(self):
        self.run = True
        self.runs = 0
        self.num_lines = 0

    def _read_log(self, lines=50):
        """Returns lines from a log file.

        Open Log file and read the last n lines.

        :param lines: ``dict``
        """
        log_file = APP_CONFIG.get('zimbra_log')
        if not os.path.exists(log_file):
            raise SystemExit('Log File "%s" not found' % log_file)

        with open(log_file, 'rb') as f:
            open_log = f.readlines()

        num_lines = len(open_log)
        diff_lines = num_lines - self.num_lines
        LOG.debug('New lines read in from the log "%s"', diff_lines)
        if diff_lines < 0:
            self.num_lines = num_lines
            return open_log[-lines:]
        elif diff_lines == 0:
            LOG.debug('No change in logging, nothing to process')
            return []
        else:
            self.num_lines = num_lines
            return open_log[-diff_lines:]

    def _check(self, wait=300):
        """Check for "DelegateAuthRequest" in log line.

        If the string is found, send an email the accountName information.
        """
        log_output = self._read_log()
        check = []
        for line in log_output:
            if 'cmd=DelegateAuth' in line:
                try:
                    _filter = line.split()
                    data = [' '.join([_filter[0], _filter[1]])]

                    for string in _filter:
                        if string.startswith('accountId'):
                            data.append(string.split('=')[1].rstrip(';'))
                        if string.startswith('accountName'):
                            data.append(string.split('=')[1].rstrip(';'))

                except Exception:
                    pass
                else:
                    if data:
                        LOG.warn(
                            'Authentication Delegation Detected from'
                            ' AccountID: "%s" with AccountName: "%s"'
                            % (data[1], data[2])
                        )
                        check.append(data)

        if check:
            for msg in check:
                msg.append(HOSTNAME)
                mail_message = MESSAGE % tuple(msg)
                Mailer(message=mail_message)

        time.sleep(wait)

    def stop(self, *args):
        """Stop the application."""
        LOG.debug('Stopping Log Read: %s', args)
        LOG.warn('Stopping Log Read at %s.', _get_time())
        os.kill(os.getpid(), signal.SIGKILL)
        self.run = False

    def start(self):
        """Start the application.

        The application will wait for the given amount of time between runs.

        :param wait: ``int``
        """
        LOG.info('Starting Log Read at %s.', _get_time())
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGHUP, self.stop)
        interval = APP_CONFIG.get('check_interval', 300)

        while self.run:
            self.runs += 1
            LOG.debug('Number times this has run %s', self.run)
            self._check(wait=interval)


def executable():
    """Run the main Program."""
    LOG.debug(APP_CONFIG)
    prog = LogRead()
    prog.start()


# Load Application Configuration
APP_NAME = 'zimbra_delegate'
CONFIG = ConfigurationSetup()
APP_CONFIG = {}
APP_CONFIG.update(CONFIG.config_args(section='default'))
APP_CONFIG.update(CONFIG.config_args(section='mail'))

# Load Logging
logger_setup(name=APP_NAME, debug_logging=APP_CONFIG.get('debug'))
LOG = logging.getLogger(name=APP_NAME)

# Load Hostname
HOSTNAME = platform.node()

# Load Message
MESSAGE = """
Hello,

This message to let you know that a "DelegateAuth" request has been performed

Time: "%s"
Account ID: "%s"
Account name: "%s"
Server: "%s"

If this is an out-of-band request please login to the server and begin
reviewing this security of the server and or Zimbra.

Thank you.
"""


if __name__ == '__main__':
    executable()
