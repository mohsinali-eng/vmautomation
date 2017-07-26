#!/usr/bin/env python

import requests
import progressbar
import time
import sys
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl
import ssl


class FailedToConnect(Exception):
    """
    Failed to Connect Exception
    """

    def __init__(self, msg="Failed to Connect Exception"):
        super(FailedToConnect, self).__init__(msg)


class ESXHost(object):
    """
    ESX Host class to manage connection, different objects and task progress
    """

    def __init__(self, host, username, password, port, logger, ssl_check):
        """
        Constructor for ESXHost
        Args:
            host:       (str): ESX(Vmware VSphere) hostname
            username:   (str): username to authenticate into host
            password:   (str): password to authenticate into host
            port:       (int): port number for connection
            logger:     (obj): Logger object to manage logging
            ssl_check:  (bool): False to disable SSL Check and True to enable it
        """
        self.connection_obj = None
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.logger = logger
        self.ssl_check = ssl_check
        self.__connect_to_esx()

    def get_success_message(self, msg_content):
        """
        Get success colored message
        Args:
            msg_content:    (str): message content
        Returns:
            str:            Return success message
        """
        return "{0}{1}{2}".format("\x1b[6;30;42m", msg_content, "\x1b[0m")

    def get_failure_message(self, msg_content):
        """
        Get failure colored message
        Args:
            msg_content:    (str): message content
        Returns:
            str:            Return failure message
        """
        return "{0}{1}{2}".format("\x1b[0;30;41m", msg_content, "\x1b[0m")

    def get_informative_message(self, msg_content):
        """
        Get informative colored message
        Args:
            msg_content:    (str): message content
        Returns:
            str:            Return informative message
        """
        return "{0}{1}{2}".format("\x1b[6;30;44m", msg_content, "\x1b[0m")

    def __connect_to_esx(self):
        """
        Private method to connect to esx
        This will be called everytime ESX host has been initialized
        """
        ssl_context = None
        if not self.ssl_check:
            self.logger.debug('Disabling SSL certificate verification.')
            requests.packages.urllib3.disable_warnings()
            if hasattr(ssl, 'SSLContext'):
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
                ssl_context.verify_mode = ssl.CERT_NONE
        try:
            self.logger.info(
                'Connecting to server {0}:{1} with username {2}'.format(self.host, self.port, self.username))
            if ssl_context:
                self.connection_obj = SmartConnect(host=self.host, user=self.username, pwd=self.password,
                                                   port=int(self.port), sslContext=ssl_context)
            else:
                self.connection_obj = SmartConnect(host=self.host, user=self.username, pwd=self.password,
                                                   port=int(self.port))
        except (ssl.SSLError, IOError, vim.fault.InvalidLogin) as exception:
            self.logger.error('{0} while connecting to server {1}:{2} with username {3}'.format(
                exception, self.host, self.port, self.username))
        if not self.connection_obj:
            self.logger.error('Could not connect to host {0} with user {1} and specified password'.format(
                self.get_failure_message("{0}:{1}".format(self.host, self.port)), self.username))
            raise FailedToConnect(msg="Failed to connect to {0}:{1} using username ({2})"
                                  .format(self.host, self.port, self.username))
        else:
            self.logger.info(
                'Successfully connected to server {0}:{1} with username {2}'.format(self.host, self.port,
                                                                                    self.username))

    def get_obj(self, obj_name, obj_type):
        """
        Find an object in ESXHost by it's obj_name and obj_type
        Args:
            obj_type:       (obj): ESXHost object type
            obj_name:       (str): ESXHost object name in string format
        Returns:
            obj:            ESXHost object reference
        """
        content = self.connection_obj.content
        obj_list = content.viewManager.CreateContainerView(content.rootFolder, obj_type, True).view
        for obj in obj_list:
            sys.stdout.write('Checking object "{0}"                      \r'.format(obj.name))
            if obj.name == obj_name:
                self.logger.info('Found object {0}'.format(self.get_success_message(obj.name)))
                return obj
            else:
                sys.stdout.flush()
        return None

    def task_progress(self, task_obj, vm_name):
        """
        Get the real time progress of a task from ESXHost
        Args:
            task_obj:       (obj): ESXHost task object
            vm_name:        (str): Virtual Machine Name
        Returns:
            obj:            Virtual Machine object of a finished task
        """
        self.logger.info('{0} - Checking task for completion. This might take a while'.format(vm_name))
        self.logger.debug('{0} - Checking {1} task'.format(vm_name, task_obj.info.descriptionId))
        widgets = [
            '{0}{1}{2} - {3}: '.format("\x1b[6;30;42m", vm_name, "\x1b[0m", task_obj.info.descriptionId),
            progressbar.Percentage(),
            ' | ', progressbar.ETA()]
        while True:
            if task_obj.info.state == vim.TaskInfo.State.success:
                self.logger.info(
                    '{0} - {1} task is done'.format(vm_name, self.get_success_message(task_obj.info.descriptionId)))
                vm_obj = task_obj.info.result
                break
            elif task_obj.info.state == vim.TaskInfo.State.running:
                with progressbar.ProgressBar(widgets=widgets, max_value=100) as bar:
                    bar.start()
                    bar.update(0)
                    while task_obj.info.state == vim.TaskInfo.State.running:
                        time.sleep(1)
                        bar.update(task_obj.info.progress)
            elif task_obj.info.state == vim.TaskInfo.State.queued:
                self.logger.warning('{0} - {1} task is queued'.format(vm_name, task_obj.info.descriptionId))
            elif task_obj.info.state == vim.TaskInfo.State.error:
                if task_obj.info.error.msg:
                    self.logger.error('{0} - {1} task has quit with error: {2}'.format(
                        vm_name, self.get_failure_message(task_obj.info.descriptionId), task_obj.info.error.msg))
                else:
                    self.logger.error(
                        '{0} - {1} task has quit with cancelation'.format(vm_name, self.get_failure_message(
                            task_obj.info.descriptionId)))
                vm_obj = None
                break
            else:
                vm_obj = None
                break
        return vm_obj

    def __del__(self):
        """
        Magic method to disconnect from ESXHost
        This will be called automatically at exit.
        """
        if self.connection_obj:
            self.logger.info('Disconnecting from host {0}:{1}'.format(self.host, self.port))
            Disconnect(self.connection_obj)
