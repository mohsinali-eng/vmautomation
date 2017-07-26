#!/usr/bin/env python

from pyVmomi import vim, vmodl
from host import ESXHost


class VirtualMachineNotFound(Exception):
    """
    Virtual Machine Not Found Exception
    """

    def __init__(self, msg="Virtual Machine Not Found"):
        super(VirtualMachineNotFound, self).__init__(msg)

class VirtualMachineCreationFailure(Exception):
    """
    Virtual Machine Creation Failure Exception
    """

    def __init__(self, msg="Virtual Machine Creation Failure Exception"):
        super(VirtualMachineCreationFailure, self).__init__(msg)


class VirtualMachineCloningFailure(Exception):
    """
    Virtual Machine Cloning Failure Exception
    """

    def __init__(self, msg="Virtual Machine Cloning Failure Exception"):
        super(VirtualMachineCloningFailure, self).__init__(msg)


class VirtualMachineAlreadyExist(Exception):
    """
    Virtual Machine Already Exist Exception
    """

    def __init__(self, msg="Virtual Machine Already Exist"):
        super(VirtualMachineAlreadyExist, self).__init__(msg)


class ResourcePoolNotFound(Exception):
    """
    Resource Pool Not Found Exception
    """

    def __init__(self, msg="Resource Pool Not Found"):
        super(ResourcePoolNotFound, self).__init__(msg)


class TemplateNotFound(Exception):
    """
    Template Not Found Exception
    """

    def __init__(self, msg="Template Not Found"):
        super(TemplateNotFound, self).__init__(msg)


class DatacenterNotFound(Exception):
    """
    Datacenter Not Found Exception
    """

    def __init__(self, msg="Datacenter Not Found"):
        super(DatacenterNotFound, self).__init__(msg)


class DatastoreNotFound(Exception):
    """
    Datastore Not Found Exception
    """

    def __init__(self, msg="Datastore Not Found"):
        super(DatastoreNotFound, self).__init__(msg)


class FolderNotFound(Exception):
    """
    Folder Not Found Exception
    """

    def __init__(self, msg="Folder Not Found"):
        super(FolderNotFound, self).__init__(msg)


class VirtualMachine(ESXHost):
    """
    Virtual Machine class to manage Virtual machines/Template from a ESXHost
    """

    def __init__(self, host, username, password, port, logger, ssl_check, vm_name):
        """
        Constructor for VirtualMachine
        Args:
            host:       (str): ESX(Vmware VSphere) hostname
            username:   (str): username to authenticate into host
            password:   (str): password to authenticate into host
            port:       (int): port number for connection
            logger:     (obj): Logger object to manage logging
            ssl_check:  (bool): False to disable SSL Check and True to enable it
            vm_name:    (str):  Virtual machine name which will be automated
        """
        super(VirtualMachine, self).__init__(host, username, password, port, logger, ssl_check)
        self.vm_name = vm_name
        self.vm_obj = None
        self.template_obj = None
        self.resource_pool_obj = None
        self.datastore_obj = None
        self.datacenter_obj = None
        self.folder_obj = None

    # All private methods to configure virtual machine
    def __is_vm_exist(self):
        """
        To Check is the virtual machine exist
        """
        if self.get_obj(self.vm_name, [vim.VirtualMachine]):
            return True
        else:
            return False

    def __set_relocate_spec(self):
        """
        To set relocate specification
        This will be called whenever datastore_obj or resource_pool_obj has been changed
        """
        self.logger.info("{0} - creating relocate spec for VM {0}".format(self.vm_name))
        self.relocate_spec = vim.vm.RelocateSpec()
        self.relocate_spec.pool = self.resource_pool_obj
        self.relocate_spec.datastore = self.datastore_obj

    def __get_virtual_nic_device(self, nic_hw_name):
        """
        To get virtual NIC Device object based on provided NIC Hardware Name
        Args:
            nic_hw_name:       (str): NIC Hardware Name
        Return:
            (obj):              Virtual Ethernet Card Object
        """
        self.logger.info('{0} - Trying to get Virtual NIC Device: {1}'.format(self.vm_name, nic_hw_name))
        virtual_nic_device = None
        if not self.vm_obj:
            self.logger.error(
                '{0} - Virtual Machine ({1}) not found'.format(self.vm_name, self.get_failure_message(self.vm_name)))
            raise VirtualMachineNotFound(msg="VM: {0} not found".format(self.vm_name))
        for dev in self.vm_obj.config.hardware.device:
            if isinstance(dev, vim.vm.device.VirtualEthernetCard) \
                    and dev.deviceInfo.label == nic_hw_name:
                virtual_nic_device = dev
        if not virtual_nic_device:
            raise RuntimeError('Virtual NIC:{0} not found.'.format(nic_hw_name))
        return virtual_nic_device

    def __get_free_ide_controller(self):
        """
        To get free IDE Controller
        Return:
            (obj):              Free IDE Controller object
        """
        self.logger.debug("{0} - Getting free IDE Controller".format(self.vm_name))
        for dev in self.vm_obj.config.hardware.device:
            if isinstance(dev, vim.vm.device.VirtualIDEController):
                # If there are less than 2 devices attached, we can use it.
                if len(dev.device) < 2:
                    return dev
        self.logger.warning("{0} - Couldn't get free IDE controller".format(self.vm_name))
        return None

    def __reconfigure_vm(self, vm_spec=None, vm_device_changes=None):
        """
        Reconfigure Virtual Machine with new spec and changed device spec
        Args:
            vm_spec:                (obj): Virtual Machine spec. Default is None
            vm_device_changes:      (obj): Changed virtual device specs
        """
        self.logger.info('{0} - Reconfiguring virtual machine'.format(self.vm_name))
        if vm_spec:
            vm_device_changes = [vm_spec]
        spec = vim.vm.ConfigSpec()
        spec.deviceChange = vm_device_changes
        reconfigure_task_obj = self.vm_obj.ReconfigVM_Task(spec=spec)
        self.task_progress(reconfigure_task_obj, self.vm_name)

    def __get_clone_spec(self):
        """
        Create and Return virtual machine cloning operation spec
        Return:
            VM Cloning spec:              VM Cloning operation spec
        """
        self.logger.debug('{0} - Creating clone spec'.format(self.vm_name))
        clone_spec = vim.vm.CloneSpec(powerOn=False, template=False, location=self.relocate_spec)
        return clone_spec

    def __get_disk_spec(self, unit_number, controller, disk_label, capacity_in_KB):
        """
        Get disk spec
        You will use this method to get specification to add new hard drive
        Args:
            unit_number:                (int): Hard drive unit number
            controller:                 (obj): Virtual Device spec controller
            disk_label:                 (str): Disk label for new hard drive
            capacity_in_KB:             (int): Hard drive capacity in KB
        Return:
            vm_disk_spec:                Spec for disk add operation
        """
        self.logger.info('{0} - Getting hard drive spec for {1}'.format(self.vm_name, disk_label))
        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.fileOperation = "create"
        disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        disk_spec.device = vim.vm.device.VirtualDisk()
        disk_spec.device.backing = \
            vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
        disk_spec.device.backing.thinProvisioned = True
        disk_spec.device.backing.diskMode = 'persistent'
        disk_spec.device.backing.fileName = '[{0}] {1}/{1}-{2}.vmdk'.format(self.datastore_obj.name, self.vm_name,
                                                                            disk_label)
        disk_spec.device.unitNumber = unit_number
        disk_spec.device.capacityInKB = long(capacity_in_KB)
        disk_spec.device.controllerKey = controller.key
        return disk_spec

    # Helper methods to set different VM Objects
    def set_vm_obj(self):
        """
        To set virtual machine object
        """
        self.logger.info("{0} - Setting VM object of ({0})".format(self.vm_name))
        self.vm_obj = self.get_obj(self.vm_name, [vim.VirtualMachine])
        if not self.vm_obj:
            self.logger.warning(
                '{0} - Unable to find VM {1}'.format(self.vm_name, self.get_failure_message(self.vm_name)))
        else:
            self.logger.info('{0} - Virtual Machine ({0}) found'.format(self.vm_name))

    def set_template_obj(self, template_name):
        """
        To set template object using template name
        We will call this after initializing VM object from outside
        Args:
            template_name:       (str): Template Name
        """
        self.logger.info('{0} - Setting template object of {1}'.format(self.vm_name, template_name))
        self.template_obj = self.get_obj(template_name, [vim.VirtualMachine])
        if not self.template_obj:
            self.logger.error(
                '{0} - Unable to find template {1}'.format(self.vm_name, self.get_failure_message(template_name)))
            raise TemplateNotFound(msg="Template: {0} not found".format(template_name))
        else:
            self.logger.info('%s - Template %s found' % (self.vm_name, template_name))

    def set_datacenter_obj(self, datacenter=None):
        """
        To set datacenter object using datacenter name
        We will call this after initializing VM object from outside
        Args:
            datacenter:       (str): Datacenter Name, Default is None
        """
        self.logger.info('{0} - Setting Datacenter object'.format(self.vm_name))
        if datacenter:
            self.logger.debug('{0} - Finding Datacenter: {1}'.format(self.vm_name, datacenter))
            self.datacenter_obj = self.get_obj(datacenter, [vim.Datacenter])
        else:
            self.logger.debug('{0} - Trying to use rootFolder as Datacenter'.format(self.vm_name))
            self.datacenter_obj = self.connection_obj.content.rootFolder.childEntity[0]
        if not self.datacenter_obj:
            self.logger.error(
                '{0} - Unable to find Datacenter {1}'.format(self.vm_name, self.get_failure_message(datacenter)))
            raise DatacenterNotFound(msg="Datacenter: {0} not found".format(datacenter))
        else:
            self.logger.info('{0} - Datacenter: {1} found'.format(self.vm_name,
                                                                  self.datacenter_obj.name))

    def set_datastore_obj(self, datastore=None):
        """
        To set datastore object using datastore name
        We will call this after initializing VM object from outside
        Args:
            datastore:       (str): Datastore Name, Default is None
        """
        self.logger.info('{0} - Setting Datastore object'.format(self.vm_name))
        if datastore:
            self.logger.debug('{0} - Finding Datastore: {1}'.format(self.vm_name, datastore))
            self.datastore_obj = self.get_obj(datastore, [vim.Datastore])
        if self.template_obj and not self.datastore_obj:
            self.logger.debug('{0} - Getting Template Datastore'.format(self.vm_name))
            self.datastore_obj = self.get_obj(self.template_obj.datastore[0].info.name, [vim.Datastore])
        if not self.datastore_obj:
            self.logger.error(
                '{0} - Unable to find Datastore {1}'.format(self.vm_name, self.get_failure_message(datastore)))
            raise DatastoreNotFound(msg="Datastore: {0} not found".format(datastore))
        else:
            self.logger.info('{0} - Datastore: {1} found'.format(self.vm_name,
                                                                 self.datastore_obj.name))
            self.__set_relocate_spec()

    def set_resource_pool_obj(self, resource_pool=None):
        """
        To set resource_pool object using resource pool name
        We will call this after initializing VM object from outside
        Args:
            resource_pool:       (str): Resource Pool Name, Default is None
        """
        self.logger.info('{0} - Setting Resource Pool object'.format(self.vm_name))
        if resource_pool:
            self.logger.debug('{0} - Finding Resource Pool: {1}'.format(self.vm_name, resource_pool))
            self.resource_pool_obj = self.get_obj(resource_pool, [vim.ResourcePool])
        else:
            self.logger.info(
                '{0} - No resource pool specified thus using the default resource pool.'.format(self.vm_name))
            self.resource_pool_obj = self.get_obj('Resources', [vim.ResourcePool])
        if self.resource_pool_obj is None:
            self.logger.error(
                '{0} - Unable to find Resource Pool {1}'.format(self.vm_name,
                                                                self.get_failure_message(resource_pool)))
            raise ResourcePoolNotFound(msg="Resource Pool: {0} not found".format(resource_pool))
        else:
            self.logger.info('{0} - Resource Pool: {1} found'.format(self.vm_name, self.resource_pool_obj.name))
            self.__set_relocate_spec()

    def set_folder_obj(self, folder_name=None):
        """
        To set folder object using folder name
        We will call this after initializing VM object from outside
        Args:
            folder_name:       (str): Folder Name, Default is None
        """
        self.logger.info('{0} - Setting Folder object'.format(self.vm_name))
        if folder_name:
            self.logger.debug('{0} - Finding Folder: {1}'.format(self.vm_name, folder_name))
            self.folder_obj = self.get_obj(folder_name, [vim.Folder])
        elif self.datacenter_obj:
            self.logger.info(
                '{0} - Setting folder to datacenter root folder as a datacenter has been defined'.format(self.vm_name))
            self.folder_obj = self.datacenter_obj.vmFolder
        elif self.template_obj:
            self.logger.info('{0} - Setting folder to template folder as default'.format(self.vm_name))
            self.folder_obj = self.template_obj.parent
        if self.folder_obj is None:
            self.logger.error(
                '{0} - Unable to find folder {1}'.format(self.vm_name, self.get_failure_message(folder_name)))
            raise FolderNotFound(msg="Folder: {0} not found".format(folder_name))
        else:
            self.logger.info('{0} - Folder: {1} found'.format(self.vm_name, self.folder_obj.name))

    # Add new hardware to virtual machine
    def add_hard_disk(self, disk_label, capacity_in_KB):
        """
        Main method to add new hard drive
        Just specify hard drive label and capacity in KB
        Args:
            disk_label:                 (str): Disk label for new hard drive
            capacity_in_KB:             (int): Hard drive capacity in KB
        """
        self.logger.info(
            '{0} - Adding hard drive {1} with size {2} KB'.format(self.vm_name,
                                                                  self.get_informative_message(disk_label),
                                                                  capacity_in_KB))
        dev_changes = []
        controller = None
        for dev in self.vm_obj.config.hardware.device:
            if hasattr(dev.backing, 'fileName'):
                unit_number = int(dev.unitNumber) + 1
                # unit_number 7 reserved for scsi controller
                if unit_number == 7:
                    unit_number += 1
            if isinstance(dev, vim.vm.device.VirtualSCSIController):
                controller = dev
        if not controller:
            self.logger.debug('{0} - Adding scsi controller for first hard drive'.format(self.vm_name))
            scsi_ctr = vim.vm.device.VirtualDeviceSpec()
            scsi_ctr.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
            scsi_ctr.device = vim.vm.device.VirtualLsiLogicController()
            scsi_ctr.device.deviceInfo = vim.Description()
            scsi_ctr.device.slotInfo = vim.vm.device.VirtualDevice.PciBusSlotInfo()
            scsi_ctr.device.slotInfo.pciSlotNumber = 16
            scsi_ctr.device.controllerKey = 100
            scsi_ctr.device.unitNumber = 3
            scsi_ctr.device.busNumber = 0
            scsi_ctr.device.hotAddRemove = True
            scsi_ctr.device.sharedBus = 'noSharing'
            scsi_ctr.device.scsiCtlrUnitNumber = 7
            dev_changes.append(scsi_ctr)
            disk_spec = self.__get_disk_spec(unit_number=0, controller=scsi_ctr.device,
                                             disk_label=disk_label, capacity_in_KB=capacity_in_KB)
            dev_changes.append(disk_spec)
            self.__reconfigure_vm(vm_device_changes=dev_changes)
        else:
            disk_spec = self.__get_disk_spec(unit_number=unit_number, controller=controller,
                                             disk_label=disk_label, capacity_in_KB=capacity_in_KB)
            self.__reconfigure_vm(vm_spec=disk_spec)

    def add_cdrom(self, iso_file_name=None, startConnected=False):
        """
        Main method to add new CDROM
        just specify iso file name which will be attached to CDROM
        We expect iso filename as specific structure like "[<ISO datastore name>] <iso_file.iso>"
        Args:
            iso_file_name:                (str): "[<ISO datastore name>] <iso_file.iso>", default is None
            startConnected:               (bool): Connected from power on, default is False
        """
        self.logger.info(
            '{0} - Adding {1} drive with connected({2}) from startup'.format(self.vm_name,
                                                                             self.get_informative_message("CDROM"),
                                                                             startConnected))
        controller = self.__get_free_ide_controller()
        if iso_file_name:
            self.logger.info('{0} - Adding ISO {1} to CDROM drive'.format(self.vm_name, iso_file_name))
            backing = vim.vm.device.VirtualCdrom.IsoBackingInfo(fileName=iso_file_name)
        else:
            backing = vim.vm.device.VirtualCdrom.RemotePassthroughBackingInfo()
        connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        connectable.allowGuestControl = True
        connectable.startConnected = startConnected
        virtual_cdrom = vim.vm.device.VirtualCdrom()
        virtual_cdrom.controllerKey = controller.key
        virtual_cdrom.key = -1
        virtual_cdrom.connectable = connectable
        virtual_cdrom.backing = backing
        cdrom_spec = vim.vm.device.VirtualDeviceSpec()
        cdrom_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        cdrom_spec.device = virtual_cdrom
        self.__reconfigure_vm(vm_spec=cdrom_spec)

    def add_network_card(self, network_label, mac_address=None, mac_address_type='manual',
                         connected=True, summary="VSphere Network"):
        """
        Main method to add new network card
        If mac address type is manual then we will add new mac address only
        Args:
            network_label:                   (str): New Network label for Newly added NIC
            mac_address:                     (str): Provided mac address, default is None
            mac_address_type:                (str): manual or assigned, default is None
            connected:                       (bool): connected from startup or not, default is True
            summary:                         (str): Network card summary
        """
        self.logger.info(
            '{0} - Adding Network Card {1}'.format(self.vm_name, self.get_informative_message(network_label)))
        nic_spec = vim.vm.device.VirtualDeviceSpec()
        nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        nic_spec.device = vim.vm.device.VirtualE1000()
        nic_spec.device.deviceInfo = vim.Description()
        nic_spec.device.deviceInfo.summary = summary
        nic_spec.device.backing = \
            vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
        nic_spec.device.backing.useAutoDetect = False
        nic_spec.device.backing.network = self.get_obj(network_label, [vim.Network])
        nic_spec.device.backing.deviceName = network_label
        nic_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        nic_spec.device.connectable.startConnected = True
        nic_spec.device.connectable.allowGuestControl = True
        nic_spec.device.connectable.connected = connected
        nic_spec.device.connectable.status = 'untried'
        nic_spec.device.wakeOnLanEnabled = True
        if mac_address_type == "manual" and mac_address:
            self.logger.debug('{0} - Adding mac address {1} to {2}'.format(self.vm_name, mac_address, network_label))
            nic_spec.device.macAddress = mac_address
            nic_spec.device.addressType = mac_address_type
        else:
            self.logger.debug('{0} - Using assigned mac address'.format(self.vm_name))
            nic_spec.device.addressType = 'assigned'
        self.__reconfigure_vm(vm_spec=nic_spec)

    # Update virtual machine's settings
    def update_mac_address(self, nic_hw_name, mac_address):
        """
        Main method to update mac address from existing NIC
        Args:
            nic_hw_name:                     (str): Network card name
            mac_address:                     (str): Mac address
        """
        self.logger.info(
            '{0} - Updating mac address to {1} for {2}'.format(self.vm_name, self.get_informative_message(mac_address),
                                                               nic_hw_name))
        virtual_nic_device = self.__get_virtual_nic_device(nic_hw_name)
        virtual_nic_spec = vim.vm.device.VirtualDeviceSpec()
        virtual_nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        virtual_nic_spec.device = virtual_nic_device
        virtual_nic_spec.device.key = virtual_nic_device.key
        virtual_nic_spec.device.macAddress = mac_address
        virtual_nic_spec.device.addressType = 'manual'
        virtual_nic_spec.device.backing = virtual_nic_device.backing
        virtual_nic_spec.device.backing.deviceName = virtual_nic_device.backing.deviceName
        virtual_nic_spec.device.wakeOnLanEnabled = virtual_nic_device.wakeOnLanEnabled
        self.__reconfigure_vm(vm_spec=virtual_nic_spec)

    def update_network_label(self, nic_hw_name, new_network_label):
        """
        Main method to update network label from existing NIC
        Args:
            nic_hw_name:                     (str): Network card name
            new_network_label:               (str): New Network Label
        """
        self.logger.info('{0} - Updating network label name to {1}'.format(self.vm_name, self.get_informative_message(
            new_network_label)))
        virtual_nic_device = self.__get_virtual_nic_device(nic_hw_name)
        virtual_nic_spec = vim.vm.device.VirtualDeviceSpec()
        virtual_nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        virtual_nic_spec.device = virtual_nic_device
        virtual_nic_spec.device.backing.deviceName = new_network_label
        self.__reconfigure_vm(vm_spec=virtual_nic_spec)

    def update_nic_state(self, nic_hw_name, connected=True):
        """
        Main method to update network device state from existing NIC
        Args:
            nic_hw_name:                     (str): Network card name
            connected:                       (bool): Connected from start up or not
        """
        self.logger.info('{0} - Updating network device status to {1}'.format(self.vm_name,
                                                                              self.get_informative_message(
                                                                                  "connected/disconnected")))
        virtual_nic_device = self.__get_virtual_nic_device(nic_hw_name)
        connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        if connected:
            self.logger.debug('{0} - Updating network device status to connected'.format(self.vm_name))
        else:
            self.logger.debug('{0} - Updating network device status to disconnected'.format(self.vm_name))
        connectable.connected = connected
        connectable.startConnected = connected
        virtual_nic_spec = vim.vm.device.VirtualDeviceSpec()
        virtual_nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        virtual_nic_spec.device = virtual_nic_device
        virtual_nic_spec.device.connectable = connectable
        self.__reconfigure_vm(vm_spec=virtual_nic_spec)

    # Common actions to virtual machine
    def power_on(self):
        """
        Main method to power on Virtual Machine
        """
        self.logger.info('{0} - Power On virtual machine'.format(self.vm_name))
        self.set_vm_obj()
        if not self.vm_obj:
            self.logger.error(
                '{0} - Virtual Machine ({1}) not found'.format(self.vm_name, self.get_failure_message(self.vm_name)))
            raise VirtualMachineNotFound(msg="VM: {0} not found".format(self.vm_name))
        power_on_vm_task_obj = self.vm_obj.PowerOn()
        self.task_progress(power_on_vm_task_obj, self.vm_name)

    def power_off(self):
        """
        Main method to power off Virtual Machine
        """
        self.logger.info('{0} - Power Off virtual machine'.format(self.vm_name))
        self.set_vm_obj()
        if not self.vm_obj:
            self.logger.error(
                '{0} - Virtual Machine ({1}) not found'.format(self.vm_name, self.get_failure_message(self.vm_name)))
            raise VirtualMachineNotFound(msg="VM: {0} not found".format(self.vm_name))
        power_off_vm_task_obj = self.vm_obj.PowerOff()
        self.task_progress(power_off_vm_task_obj, self.vm_name)

    def reset(self):
        """
        Main method to Reset Virtual Machine
        """
        self.logger.info('{0} - Resetting virtual machine'.format(self.vm_name))
        self.set_vm_obj()
        if not self.vm_obj:
            self.logger.error(
                '{0} - Virtual Machine ({1}) not found'.format(self.vm_name, self.get_failure_message(self.vm_name)))
            raise VirtualMachineNotFound(msg="VM: {0} not found".format(self.vm_name))
        reset_vm_task_obj = self.vm_obj.Reset()
        self.task_progress(reset_vm_task_obj, self.vm_name)

    def delete(self):
        """
        Main method to delete Virtual Machine
        """
        self.logger.info('{0} - Deleting virtual machine'.format(self.vm_name))
        self.set_vm_obj()
        if not self.vm_obj:
            self.logger.error(
                '{0} - Virtual Machine ({1}) not found'.format(self.vm_name, self.get_failure_message(self.vm_name)))
            raise VirtualMachineNotFound(msg="VM: {0} not found".format(self.vm_name))
        delete_vm_task_obj = self.vm_obj.Destroy()
        self.task_progress(delete_vm_task_obj, self.vm_name)

    def clone_from_template(self, template_name):
        """
        Main method to clone Virtual Machine from a template
        Args:
            template_name:                     (str): Template Name
        """
        self.logger.info('{0} - Cloning virtual machine from template ({1})'.format(self.vm_name, template_name))
        self.set_template_obj(template_name)
        self.set_vm_obj()
        clone_spec = self.__get_clone_spec()
        if self.vm_obj:
            self.logger.error(
                '{0} - Virtual Machine ({1}) already exist'.format(self.vm_name,
                                                                   self.get_failure_message(self.vm_name)))
            raise VirtualMachineAlreadyExist(msg="VM: {0} already exist".format(self.vm_name))
        clone_vm_task_obj = self.template_obj.Clone(name=self.vm_name, folder=self.folder_obj, spec=clone_spec)
        self.logger.info('{0} - Cloning task created'.format(self.vm_name))
        self.vm_obj = self.task_progress(clone_vm_task_obj, self.vm_name)
        if not self.vm_obj:
            self.logger.error(
                '{0} - Failed to clone VM {1} from template {2}'.format(self.vm_name,
                                                                        self.get_failure_message(self.vm_name),
                                                                        template_name))
            raise VirtualMachineCloningFailure(msg="Failed to Clone VM ({0}) from template ({1})".format(self.vm_name,
                                                                                                         template_name))

    def create(self, memory_in_MB=4096, num_of_CPUs=1, guest_OS_id='otherGuest64', version='vmx-08'):
        """
        Main method to create Virtual Machine
        Args:
            memory_in_MB:                    (int): Memory in Megabytes; default: 4096
            num_of_CPUs:                     (int): Number of CPUs; default: 1
            guest_OS_id:                     (str): Guest OS ID; default: otherGuest64
            version:                         (str): Virtual Machine version; default: vmx-08
        """
        self.set_vm_obj()
        if self.vm_obj:
            self.logger.error(
                '{0} - Virtual Machine ({1}) already exist'.format(self.vm_name,
                                                                   self.get_failure_message(self.vm_name)))
            raise VirtualMachineAlreadyExist(msg="VM: {0} already exist".format(self.vm_name))
        datastore_path = "[{0}] {1}/{1}.vmx".format(self.datastore_obj.name, self.vm_name)
        vmx_file = vim.vm.FileInfo(logDirectory=None,
                                   snapshotDirectory=None,
                                   suspendDirectory=None,
                                   vmPathName=datastore_path)
        config = vim.vm.ConfigSpec(
            name=self.vm_name,
            annotation="Virtual Machine for Continuous Integration",
            memoryMB=int(memory_in_MB),
            numCPUs=int(num_of_CPUs),
            files=vmx_file,
            guestId=guest_OS_id,
            version=version
        )
        create_vm_task = self.folder_obj.CreateVM_Task(config=config, pool=self.resource_pool_obj)
        self.vm_obj = self.task_progress(create_vm_task, self.vm_name)
        if not self.vm_obj:
            self.logger.error(
                '{0} - Failed to create VM {1}'.format(self.vm_name, self.get_failure_message(self.vm_name)))
            raise VirtualMachineCreationFailure(msg="Failed to create VM ({0})".format(self.vm_name))

    def __call__(self):
        """
        Will return dictionary of current object's information
        Return:
            (dict):              Virtual Machines information in Dictionary
        """
        return self.__dict__

    def __str__(self):
        """
        Will return current connection's information
        Return:
            (str):              Will return connection information
        """
        return "Connected to {0}:{1}".format(self.host, self.port)
