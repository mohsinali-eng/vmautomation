VM Automation
=============

Overview
--------
This tool will help you to automate different operations in virtual machine 
located in VMware vSphere.

Supported Features
------------------
Currently support different actions like
* Create Virtual Machine
* Clone Virtual Machine from a template
* Delete an existing virtual machine
* Power on a virtual machine
* Power off a virtual machine
* Reset a virtual machine

Demo
----
![vmautomation demo](demo/demo.gif)

Install required packages
-------------------------
To start installation you need `pip`

    wget -qO- https://bootstrap.pypa.io/get-pip.py | python    

To Install required python packages based on `requirements.txt`

    python -m pip install -r requirements.txt

Documentation
-------------
### Python Program
Let's perform different operations based on .json file
>
Program will ask for password if not specified
>

#### Create:
Let's create a new virtual machine in VMware vSphere using create.json.
Define virtual machine's configuration into sample_json/create.json file then run this command

    python vmautomation --host=<hostname> --username=<username> --password=<password> create --json-file sample_json/create.json

#### Clone:
Let's clone a virtual machine from a template in VMware vSphere using clone.json.
Define virtual machine's configuration into sample_json/clone.json file then run this command

    python vmautomation --host=<hostname> --username=<username> --password=<password> clone --json-file sample_json/clone.json

#### Power on:
Let's power on an existing virtual machine

    python vmautomation --host=<hostname> --username=<username> --password=<password> power-on --vm-name=<virtual_machine_name>

#### Power off:
Let's power off an existing virtual machine

    python vmautomation --host=<hostname> --username=<username> --password=<password> power-off --vm-name=<virtual_machine_name>
    
#### Reset:
Let's reset an existing virtual machine

    python vmautomation --host=<hostname> --username=<username> --password=<password> reset --vm-name=<virtual_machine_name>

#### Delete:
Let's delete an existing virtual machine

    python vmautomation --host=<hostname> --username=<username> --password=<password> delete --vm-name=<virtual_machine_name>

### Using python APIs

>
You can also add vmautomation into your python site-packages.
So that you can easily import it into your python script.
>


    #!/usr/bin/env python
    from vmautomation import virtual_machine

    # Make sure you are passing logging object based on python logging module
    ########################
    ### Create operation ###
    ########################
    # To create virtual machine object
    virtual_machine_obj = VirtualMachine(host=<hostname>, username=<username>, 
                        password=<password>, port=<port>, 
                        logger=<logging_obj>,ssl_check=<ssl_check>, 
                        vm_name=<vm_name>)
    # To set datacenter object
    virtual_machine_obj.set_datacenter_obj(datacenter=<datacenter_name>)
    # To set datastore object
    virtual_machine_obj.set_datastore_obj(datastore=<datastore_name>)
    # To set resource pool object
    virtual_machine_obj.set_resource_pool_obj(resource_pool=<resource_pool_name>)
    # To set folder object
    virtual_machine_obj.set_folder_obj(folder=<folder_name>)
    # Virtual Machine Create operation
    virtual_machine_obj.create(memory_in_MB=<memory_in_megabytes>, 
                               num_of_CPUs=<num_of_cpus>, 
                               guest_OS_id=<guest_os>, 
                               version=<virtual_machine_version>)
    ### To add/reconfigure Virtual Machine ###
    # To add a new hard drive
    virtual_machine_obj.add_hard_disk(disk_label=<label_for_new_hard_drive>),
                                      capacityin_KB=<disk_capacity_in_kilobytes>)
    # To add a new CDROM
    # To add iso file you have to specify iso datastore and iso file name
    # Otherwise put it as None, then will use client CDROM
    iso_file_name = "[{0}] {1}".format(<iso_datastore_name>, <.iso_filename>)
    virtual_machine_obj.add_cdrom(iso_file_name, 
                                  startConnected=<is_connected_from_startup>)
    # To add a new Network Card
    # Here if you specify mac address then put mac_address_type as manual
    virtual_machine_obj.add_network_card(mac_address=<mac_address>,
                                network_label=<network_card_label>,
                                mac_address_type=<manual_or_assigned>,
                                connected=<is_connected_from_startup>,
                                summary=<summary_of_network_card>)

    ##############################                        
    ### Clone VM from template ###
    ##############################
    # To create virtual machine object
    virtual_machine_obj = VirtualMachine(host=<hostname>, username=<username>, 
                        password=<password>, port=<port>, 
                        logger=<logging_obj>,ssl_check=<ssl_check>, 
                        vm_name=<vm_name>)
    # To set datacenter object
    virtual_machine_obj.set_datacenter_obj(datacenter=<datacenter_name>)
    # To set datastore object
    virtual_machine_obj.set_datastore_obj(datastore=<datastore_name>)
    # To set resource pool object
    virtual_machine_obj.set_resource_pool_obj(resource_pool=<resource_pool_name>)
    # To set folder object
    virtual_machine_obj.set_folder_obj(folder=<folder_name>)                          
    # To set template object
    virtual_machine_obj.clone_from_template(template_name=<template_name>)
    # To update mac address to a specific network card
    virtual_machine_obj.update_mac_address(nic_hdw_name=<network_card_name>, 
                                           new_mac_address=<new_mac_address>)
    # To update network label for a specific network card 
    virtual_machine_obj.update_network_label(nic_hdw_name=<network_card_name>,
                                             new_network_label=<new_network_label>)
    # To update network state for a specific network card
    virtual_machine_obj.update_nic_state(nic_hdw_name=<network_card_name>,
                                         is_connected=<network_card_is_connected>)

    ################################                        
    ### Power on virtual machine ###
    ################################
    # To create virtual machine object
    virtual_machine_obj = VirtualMachine(host=<hostname>, username=<username>, 
                        password=<password>, port=<port>, 
                        logger=<logging_obj>,ssl_check=<ssl_check>, 
                        vm_name=<vm_name>)
    virtual_machine.power_on()

    #################################                        
    ### Power off virtual machine ###
    #################################
    # To create virtual machine object
    virtual_machine_obj = VirtualMachine(host=<hostname>, username=<username>, 
                        password=<password>, port=<port>, 
                        logger=<logging_obj>,ssl_check=<ssl_check>, 
                        vm_name=<vm_name>)
    virtual_machine.power_off()

    #############################                        
    ### Reset virtual machine ###
    #############################
    # To create virtual machine object
    virtual_machine_obj = VirtualMachine(host=<hostname>, username=<username>, 
                        password=<password>, port=<port>, 
                        logger=<logging_obj>,ssl_check=<ssl_check>, 
                        vm_name=<vm_name>)
    virtual_machine.reset()

    ##############################                        
    ### Delete virtual machine ###
    ##############################
    # To create virtual machine object
    virtual_machine_obj = VirtualMachine(host=<hostname>, username=<username>, 
                        password=<password>, port=<port>, 
                        logger=<logging_obj>,ssl_check=<ssl_check>, 
                        vm_name=<vm_name>)
    virtual_machine.delete()

### Related Projects
* Python pyvmomi: https://github.com/vmware/pyvmomi
* VMware vSphere Automation SDK for Python: https://developercenter.vmware.com/web/sdk/65/vsphere-automation-python
