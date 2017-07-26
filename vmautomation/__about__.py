__title__ = 'Virtual Machine Automation for VMWare VSphere'
__package_name__ = 'vmautomation'
__author__ = 'Mohammad Mohsin Ali'
__email__ = 'mohsinalilipu@gmail.com'
__version__ = '0.1.1'
__license__ = 'MIT'
__copyright__ = '@Copyright devtoolsmith'
__url__ = ''
__suported_operations__ = """
1. Create Virtual Machine
2. Clone Virtual Machine from Template
3. Power On an existing Virtual Machine
4. Power Off an existing Virtual Machine
5. Reset an existing Virtual Machine
6. Delete an existing Virtual Machine
"""
__description__ = """
Virtual Machine Automation for VMware vSphere environment.
Currently providing automatic create and clone from a template
using certain configuration file(.json).
To create, define all configuration for virtual machine in create.json file
and pass it as an argument to the scripts
To clone from a template, define all configuration for virtual machine in clone.json file
and pass it as an argument to the scripts
We also have action support for delete,power on, power off, reset Virtual machine
"""
__in_line_description__ = ' '.join(__description__.strip().split())
