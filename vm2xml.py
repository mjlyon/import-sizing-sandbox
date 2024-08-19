import ssl
import atexit
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
from lxml import etree


def get_vm_info(vm):
    vm_info = {
        'name': vm.name,
        'memory_mb': vm.config.hardware.memoryMB,
        'cpu_count': vm.config.hardware.numCPU,
        'disks': [],
        'networks': []
    }

    # Gather disk information
    for device in vm.config.hardware.device:
        if isinstance(device, vim.vm.device.VirtualDisk):
            disk_info = {
                'label': device.deviceInfo.label,
                'size_gb': device.capacityInKB / 1024 / 1024,
                'backing_file': device.backing.fileName
            }
            vm_info['disks'].append(disk_info)

    # Gather network information
    for nic in vm.guest.net:
        nic_info = {
            'network': nic.network,
            'ip_address': nic.ipAddress
        }
        vm_info['networks'].append(nic_info)

    return vm_info


def create_xml(vm_info):
    root = etree.Element('domain', type='kvm')
    name = etree.SubElement(root, 'name')
    name.text = vm_info['name']

    memory = etree.SubElement(root, 'memory', unit='MB')
    memory.text = str(vm_info['memory_mb'])

    vcpu = etree.SubElement(root, 'vcpu')
    vcpu.text = str(vm_info['cpu_count'])

    devices = etree.SubElement(root, 'devices')

    for disk in vm_info['disks']:
        disk_element = etree.SubElement(devices, 'disk', type='file', device='disk')
        driver = etree.SubElement(disk_element, 'driver', name='qemu', type='qcow2')
        source = etree.SubElement(disk_element, 'source', file=disk['backing_file'])
        target = etree.SubElement(disk_element, 'target', dev='vda', bus='virtio')
        size = etree.SubElement(disk_element, 'size', unit='GB')
        size.text = str(disk['size_gb'])

    for nic in vm_info['networks']:
        interface = etree.SubElement(devices, 'interface', type='network')
        source = etree.SubElement(interface, 'source', network=nic['network'])
        mac = etree.SubElement(interface, 'mac', address=nic['ip_address'][0])

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')


def main():
    context = ssl._create_unverified_context()

    # vCenter credentials (fill in with your information)
    vc_host = 'your_vcenter_host'
    vc_user = 'your_username'
    vc_pass = 'your_password'

    si = SmartConnect(host=vc_host, user=vc_user, pwd=vc_pass, sslContext=context)
    atexit.register(Disconnect, si)

    content = si.RetrieveContent()

    vm_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    vm_list = vm_view.view

    for vm in vm_list:
        vm_info = get_vm_info(vm)
        xml_data = create_xml(vm_info)

        with open(f"{vm_info['name']}.xml", 'wb') as xml_file:
            xml_file.write(xml_data)

    print("VM information has been successfully exported to XML files.")


if __name__ == "__main__":
    main()
