#!/usr/bin/env python

import __about__
import argparse
import getpass
import logging
import json
from virtual_machine import VirtualMachine
from functools import wraps
import os


class ValueRequired(Exception):
    """
    Json data required Exception
    """

    def __init__(self, msg="Value required from json"):
        super(ValueRequired, self).__init__(msg)


class InvalidConfigurationFromJson(Exception):
    """
    Invalid Configuration from JSON Exception
    """

    def __init__(self, msg="Invalid Configuration from json"):
        super(InvalidConfigurationFromJson, self).__init__(msg)


class JSONFileNotFound(Exception):
    """
    Json File Not Found Exception
    """

    def __init__(self, msg="Json File Not Found"):
        super(JSONFileNotFound, self).__init__(msg)


def __get_args():
    """
    To Get all command-line argument from the program
    Returns:
        dict:   All parsed argument
    """
    parser = argparse.ArgumentParser(prog="{0}".format(__about__.__title__),
                                     description="{0}".format(__about__.__description__),
                                     add_help=True)

    auth = parser.add_argument_group('Authentication')
    auth.add_argument('--host', nargs=1, required=True,
                      help='The vCenter or ESXi host to connect to',
                      dest='host', type=str)
    auth.add_argument('--port', nargs=1, required=False,
                      help='Server port to connect to (default = 443)',
                      dest='port', type=int, default=[443])
    auth.add_argument('--username', nargs=1, required=True,
                      help='The username with which to connect to the host',
                      dest='username', type=str)
    auth.add_argument('--password', nargs=1, required=False,
                      help='If not provided then prompt to enter.',
                      dest='password', type=str, default=[""])
    auth.add_argument('-s', '--disable-SSL-certificate-verification', required=False,
                      help='Disable SSL certificate verification on connect like a switch',
                      dest='ssl_check', action='store_true', default=False)
    auth.add_argument('-d', '--debug', required=False,
                      help='Enable debug output like a switch', dest='debug',
                      action='store_true', default=False)
    auth.add_argument('-l', '--log-file', nargs=1, required=False,
                      help='log file name. default is stdout',
                      dest='log_file', type=str, default=[""])
    auth.add_argument('--version', action='version', version='%(prog)s {0}'.format(__about__.__version__))

    subparsers = parser.add_subparsers(description="Commands to perform different operation in ESX Host")
    # Create
    create_parser = subparsers.add_parser('create', help="To create a VM")
    create_parser.add_argument('--json-file', nargs=1, required=True, help='Json file containing all VM data',
                               dest='create_json_file', type=str, default=[""])
    # Delete
    delete_parser = subparsers.add_parser('delete', help='To delete an existing VM')
    delete_parser.add_argument('--vm-name', nargs=1, required=True, help='VM name', dest='vm_to_be_deleted',
                               type=str)
    # Reset
    reset_parser = subparsers.add_parser('reset', help='To reset an existing VM')
    reset_parser.add_argument('--vm-name', nargs=1, required=True, help='VM name', dest='vm_to_be_reset',
                              type=str)
    # Power On
    power_on_parser = subparsers.add_parser('power-on', help='To power on an existing VM')
    power_on_parser.add_argument('--vm-name', nargs=1, required=True, help='VM name', dest='vm_to_be_powered_on',
                                 type=str)
    # Power Off
    power_off_parser = subparsers.add_parser('power-off', help='To power off existing VM')
    power_off_parser.add_argument('--vm-name', nargs=1, required=True, help='VM name', dest='vm_to_be_powered_off',
                                  type=str)
    # Clone
    clone_parser = subparsers.add_parser('clone', help='To clone VM from template')
    clone_parser.add_argument('--json-file', nargs=1, required=True, help='Json file containing all VM data',
                              dest='clone_json_file', type=str, default=[""])
    return parser.parse_args()


def __get_value(config_dict, key, default=None, required=True):
    """
    To get value from configuration dictionary
    if required then we expect value
    Args:
        config_dict     (dict): Configuration in dict format
        key             (str):  Dict Key to get value
        default         (str or bool): Default value if Dict key is not present
        required        (bool): True or False
    Returns:
        str:            Value from dict[key]
    Raise:
        ValueRequired Exception
    """
    # Known Issue: problem if passed default=True and required=True
    value = config_dict.get(key, default)
    if not value and required:
        raise ValueRequired("Value required from json for key ({0})".format(key))
    return value


def __error_handler(called_func):
    """
    Decorator to handle exception
    Args:
        called_func  (obj): decorated function object
    Returns:
        int:    0 for success or -1 for failure/exception
    """

    @wraps(called_func)
    def func_wrapper(*args, **kwargs):
        try:
            called_func(*args, **kwargs)
            return 0
        except KeyError as exception:
            print "Missing required key('{0}') in json file".format(exception.message)
            return -1

    return func_wrapper


def __get_logger(log_file, debug):
    """
    To get logger based on python logging module
    Args:
        log_file  (str): Log Filename where log will be written
        debug     (bool): Log Debug flag

    Returns:
        obj:       Logging object
    """
    if debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    if log_file:
        logging.basicConfig(filename=log_file, format='%(asctime)s %(levelname)s %(message)s', level=log_level)
    else:
        logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=log_level)
    logger = logging.getLogger(__name__)
    return logger


def __get_config_from_json(json_file):
    """
    To get all configuration from specified json file
    Args:
        json_file  (str):  json file with all configuration
    Returns:
        dict:       All configuration in dictionary
    Raise:
        JSONFileNotFound:                   Json file not found exception
        InvalidConfigurationFromJson:       Invalid Configuration from json exception
    """
    if not os.path.exists(json_file):
        raise JSONFileNotFound("JSON file ({0}) not found".format(json_file))
    with open(json_file, 'r') as jsonfile:
        all_config = json.load(jsonfile)
    if not all_config:
        raise InvalidConfigurationFromJson(msg="Invalid/Empty Configuration from json file ({0})"
                                           .format(json_file))
    return all_config


@__error_handler
def main():
    """
    Main entry point for __main__.py
    Steps:
        1. Will take all user defined arguments
        2. Will process json configuration if passed
        3. Create or Delete or Clone Virtual Machine
    """
    # get all args
    all_args = __get_args()
    hostname = all_args.host[0]
    port = all_args.port[0]
    username = all_args.username[0]
    password = all_args.password[0]
    if not password:
        password = getpass.getpass(prompt='Enter password to login to %s for user %s: ' % (hostname, username))
    ssl_check = all_args.ssl_check
    debug = all_args.debug
    log_file = all_args.log_file[0]
    logging_obj = __get_logger(log_file, debug)
    # Get json file
    create_json_file = all_args.create_json_file[0] if hasattr(all_args, 'create_json_file') else None
    clone_json_file = all_args.clone_json_file[0] if hasattr(all_args, 'clone_json_file') else None
    vm_to_be_deleted = all_args.vm_to_be_deleted[0] if hasattr(all_args, 'vm_to_be_deleted') else None
    vm_to_be_reset = all_args.vm_to_be_reset[0] if hasattr(all_args, 'vm_to_be_reset') else None
    vm_to_be_powered_on = all_args.vm_to_be_powered_on[0] if hasattr(all_args, 'vm_to_be_powered_on') else None
    vm_to_be_powered_off = all_args.vm_to_be_powered_off[0] if hasattr(all_args, 'vm_to_be_powered_off') else None
    # Process Json file for create operation
    if create_json_file:
        all_config = __get_config_from_json(create_json_file)
    # Process Json file for Clone operation
    if clone_json_file:
        all_config = __get_config_from_json(clone_json_file)
    # Create Operation
    if create_json_file:
        vm_name = __get_value(all_config, 'vm-name', required=True)
        datacenter = __get_value(all_config, 'datacenter', required=False)
        datastore = __get_value(all_config, 'datastore', required=True)
        resource_pool = __get_value(all_config, 'resource-pool', required=True)
        folder = __get_value(all_config, 'folder', required=False)
        power_on_flag = __get_value(all_config, 'power-on', default=False, required=False)
        memory_in_MB = __get_value(all_config, 'memory-MB', default=4096, required=False)
        num_of_CPUs = __get_value(all_config, 'num-CPUs', default=1, required=False)
        guest_OS_id = __get_value(all_config, 'guest-OS-id', default="otherGuest64", required=False)
        version = __get_value(all_config, 'version', default="vmx-08", required=False)
        hard_disk_specs = __get_value(all_config, 'hard-disk', required=True)
        cd_drive_specs = __get_value(all_config, 'cd-drive', required=True)
        network_card_specs = __get_value(all_config, 'network-card', required=True)
        vm = VirtualMachine(host=hostname, username=username, password=password, port=port, logger=logging_obj,
                            ssl_check=ssl_check, vm_name=vm_name)
        vm.set_datacenter_obj(datacenter)
        vm.set_datastore_obj(datastore)
        vm.set_resource_pool_obj(resource_pool)
        vm.set_folder_obj(folder)
        vm.create(memory_in_MB, num_of_CPUs, guest_OS_id, version)
        for hard_disk_spec in hard_disk_specs:
            vm.add_hard_disk(disk_label=__get_value(hard_disk_spec, 'disk-label', required=True),
                             capacity_in_KB=__get_value(hard_disk_spec, 'capacity-KB', required=True))
        for cd_drive_spec in cd_drive_specs:
            iso_datastore = __get_value(cd_drive_spec, 'iso-datastore', default=None, required=False)
            iso_filename = __get_value(cd_drive_spec, 'iso-filename', default=None, required=False)
            is_connected = __get_value(cd_drive_spec, 'Connected', default=False, required=False)
            if iso_filename and iso_datastore:
                iso_file_name = "[{0}] {1}".format(iso_datastore, iso_filename)
            else:
                iso_file_name = None
            vm.add_cdrom(iso_file_name=iso_file_name, startConnected=is_connected)
        for network_card_spec in network_card_specs:
            vm.add_network_card(mac_address=__get_value(network_card_spec, 'mac-address', required=False),
                                network_label=__get_value(network_card_spec, 'network-label', required=True),
                                mac_address_type=__get_value(network_card_spec, 'mac-address-type', required=True),
                                connected=__get_value(network_card_spec, 'connected', default=False, required=False),
                                summary=__get_value(network_card_spec, 'summary',
                                                    default="Default summary for VM Automation",
                                                    required=False))
        if power_on_flag:
            vm.power_on()
    # Delete Operation
    if vm_to_be_deleted:
        vm = VirtualMachine(host=hostname, username=username, password=password, port=port, logger=logging_obj,
                            ssl_check=ssl_check, vm_name=vm_to_be_deleted)
        vm.power_off()
        vm.delete()
    # Reset Operation
    if vm_to_be_reset:
        vm = VirtualMachine(host=hostname, username=username, password=password, port=port, logger=logging_obj,
                            ssl_check=ssl_check, vm_name=vm_to_be_reset)
        vm.reset()
    # Power on Operation
    if vm_to_be_powered_on:
        vm = VirtualMachine(host=hostname, username=username, password=password, port=port, logger=logging_obj,
                            ssl_check=ssl_check, vm_name=vm_to_be_powered_on)
        vm.power_on()
    # power off Operation
    if vm_to_be_powered_off:
        vm = VirtualMachine(host=hostname, username=username, password=password, port=port, logger=logging_obj,
                            ssl_check=ssl_check, vm_name=vm_to_be_powered_off)
        vm.power_off()
    # Clone Operation
    if clone_json_file:
        vm_name = __get_value(all_config, 'vm-name', required=True)
        template = __get_value(all_config, 'template', required=True)
        datacenter = __get_value(all_config, 'datacenter', required=False)
        datastore = __get_value(all_config, 'datastore', required=True)
        resource_pool = __get_value(all_config, 'resource-pool', required=True)
        folder = __get_value(all_config, 'folder', required=False)
        power_on_flag = __get_value(all_config, 'power-on', default=False, required=False)
        network_card_specs = __get_value(all_config, 'network-card', required=True)
        updated_network_card_specs = __get_value(network_card_specs, 'update', required=False)
        vm = VirtualMachine(host=hostname, username=username, password=password, port=port, logger=logging_obj,
                            ssl_check=ssl_check, vm_name=vm_name)
        vm.set_datacenter_obj(datacenter)
        vm.set_datastore_obj(datastore)
        vm.set_resource_pool_obj(resource_pool)
        vm.set_folder_obj(folder)
        vm.clone_from_template(template_name=template)
        for updated_network_card_spec in updated_network_card_specs:
            nic_hdw_name = __get_value(updated_network_card_spec, 'nic-hdw-name', required=True)
            new_mac_address = __get_value(updated_network_card_spec, 'new-mac-address', required=False)
            new_network_label = __get_value(updated_network_card_spec, 'new-network-label', required=False)
            is_connected = __get_value(updated_network_card_spec, 'connected', required=False)
            if new_mac_address:
                vm.update_mac_address(nic_hdw_name, new_mac_address)
            if new_network_label:
                vm.update_network_label(nic_hdw_name, new_network_label)
            if is_connected:
                vm.update_nic_state(nic_hdw_name, is_connected)
        if power_on_flag:
            vm.power_on()


if __name__ == "__main__":
    main()
