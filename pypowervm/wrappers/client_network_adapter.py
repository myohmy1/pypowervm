# Copyright 2014, 2015 IBM Corp.
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import logging

from pypowervm import adapter as adpt
from pypowervm import util as u
import pypowervm.wrappers.constants as c
import pypowervm.wrappers.entry_wrapper as ewrap

LOG = logging.getLogger(__name__)

LOCATION_CODE = 'LocationCode'

VADPT_ROOT = 'ClientNetworkAdapter'
VADPT_SLOT_NUM = 'VirtualSlotNumber'
VADPT_MAC_ADDR = 'MACAddress'
VADPT_TAGGED_VLANS = 'TaggedVLANIDs'
VADPT_TAGGED_VLAN_SUPPORT = 'TaggedVLANSupported'
VADPT_VSWITCH = 'AssociatedVirtualSwitch'
VADPT_PVID = 'PortVLANID'


def crt_cna(pvid, vswitch_href, slot_num=None, mac_addr=None,
            addl_tagged_vlans=None):
    """Creates the Element structure for the creation of a Client Network Adpt.

    This is used when creating a new CNA for a client partition.  The POST
    of this should be done to the LogicalPartition/<UUID>/ClientNetworkAdapter.

    :param pvid: The Primary VLAN ID to use.
    :param vswitch_href: The URI that points to the Virtual Switch that will
                         support this adapter.
    :param slot_num: The Slot on the Client LPAR that should be used.  This
                     defaults to 'None', which means that the next available
                     slot will be used.
    :param mac_addr: The optional user specified mac address to use.  If left
                     as None, the system will generate one.
    :param addl_tagged_vlans: A set of additional tagged VLANs that can be
                              passed through this adapter (with client VLAN
                              adapters).

                              Input should be a space delimited string.
                              Example: '51 52 53'
                              Note: The limit is ~18 additional VLANs
    :returns: An Element that can be used for a Client Network Adapter create.
    """
    attrs = []
    if slot_num is not None:
        attrs.append(adpt.Element(VADPT_SLOT_NUM, text=str(slot_num)))
    else:
        attrs.append(adpt.Element('UseNextAvailableSlotID', text='true'))

    if mac_addr is not None:
        mac_addr = u.sanitize_mac_for_api(mac_addr)
        attrs.append(adpt.Element(VADPT_MAC_ADDR, text=mac_addr))

    if addl_tagged_vlans is not None:
        attrs.append(adpt.Element(VADPT_TAGGED_VLANS, text=addl_tagged_vlans))
        attrs.append(adpt.Element(VADPT_TAGGED_VLAN_SUPPORT, text='true'))
    else:
        attrs.append(adpt.Element(VADPT_TAGGED_VLAN_SUPPORT, text='false'))

    attrs.append(adpt.Element(VADPT_PVID, text=str(pvid)))

    # Put in the vSwitch
    vswitch_child = adpt.Element('link', attrib={'href': vswitch_href,
                                                 'rel': 'related'})
    assoc_vswitch = adpt.Element(VADPT_VSWITCH, children=[vswitch_child])
    attrs.append(assoc_vswitch)

    return adpt.Element(VADPT_ROOT, attrib=c.DEFAULT_SCHEMA_ATTR,
                        children=attrs)


class ClientNetworkAdapter(ewrap.EntryWrapper):
    """Wrapper object for ClientNetworkAdapter schema."""

    def get_slot(self):
        return int(self.get_parm_value(c.VIR_SLOT_NUM))

    def get_mac(self):
        """Returns the Mac Address for the adapter.

        Typical format would be: AABBCCDDEEFF
        The API returns a format with no colons and is upper cased.
        """
        return self.get_parm_value(c.MAC_ADDRESS)

    def get_pvid(self):
        """Returns the Port VLAN ID."""
        return self.get_parm_value_int(c.PORT_VLAN_ID)

    def get_loc_code(self):
        """The device's location code."""
        return self.get_parm_value(LOCATION_CODE)

    def get_tagged_vlans(self):
        """Returns a list of additional VLANs on this adapter.

        Only valid if tagged vlan support is on.
        """
        addl_vlans = self.get_parm_value(VADPT_TAGGED_VLANS, '')
        return [int(i) for i in addl_vlans.split(' ')]

    def is_tagged_vlan_supported(self):
        """Returns if addl tagged VLANs are supported."""
        return self.get_parm_value_bool(VADPT_TAGGED_VLAN_SUPPORT)

    def get_vswitch_uri(self):
        """Returns the URI for the associated vSwitch."""
        vswitches = self._entry.element.findall(VADPT_VSWITCH + c.DELIM +
                                                'link')
        if len(vswitches) != 1:
            return ''
        vs_elem = vswitches[0]
        return vs_elem.attrib['href']