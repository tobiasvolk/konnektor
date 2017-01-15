#!/usr/bin/env python


description = """

konnektor.py - a minimalistic network manager for FreeBSD

This script checks the link state of one or more network interfaces
and launches the dhcpcd daemon on the first interface that is
detected to be active in order to obtain IPv4 + IPv6 connectivity.

usage: konnektor.py <interface> [interface]*

"""


# Copyright (c) 2017 
# Tobias Volk <mail@tobiasvolk.de>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
# OF THE POSSIBILITY OF SUCH DAMAGE.


import subprocess
import sys
import time


class Link:
    def __init__(self, ifname):
        self.ssid = ""
        self.dhcpcd = None
        self.ifname = str(ifname)

    def is_active(self):
        # return true if link is active
        up_strs = ["active", "associated"]
        cmd = ["ifconfig", self.ifname]
        cmd_result = subprocess.check_output(cmd).decode("utf-8")
        tokens = cmd_result.split()
        for i in range(0, len(tokens)-1):
            if "ssid" == tokens[i]:
                newssid = tokens[i+1]
                if newssid != self.ssid:
                    # ssid changed, assume link down
                    self.ssid = newssid
                    return False
        for i in range(0, len(tokens)-1):
            if "status:" == tokens[i]:
                for up_str in up_strs:
                    if up_str in tokens[i+1]:
                        return True
        return False

    def get_l3addrs(self, af):
        # return list of configured L3 addresses
        l3addrs = []
        cmd = ["ifconfig", self.ifname]
        cmd_result = str(subprocess.check_output(cmd))
        tokens = cmd_result.split()
        for i in range(0, len(tokens)-1):
            if af in tokens[i]:
                l3addrs += [tokens[i+1]]
        return l3addrs

    def clear_l3addrs(self):
        # remove stale L3 addresses
        for af in ["inet6", "inet"]:
            l3addrs = self.get_l3addrs(af)
            for l3addr in l3addrs:
                cmd = ["ifconfig", self.ifname, af, l3addr, "delete"]
                cmd_result = str(subprocess.check_output(cmd))

    def dhcpcd_alive(self):
        # return true if dhcpcd is alive on this interface
        if self.dhcpcd == None:
            return False
        if self.dhcpcd.poll() != None:
            return False
        return True

    def up(self):
        # bring up dhcpcd
        if not(self.dhcpcd_alive()): 
            self.clear_l3addrs()
            cmd = ["dhcpcd", "-d", "-B", self.ifname]
            self.dhcpcd = subprocess.Popen(cmd, stderr=subprocess.PIPE)

    def down(self):
        # take down dhcpcd
        if self.dhcpcd != None:
            if self.dhcpcd.poll() == None:
                self.dhcpcd.terminate()
                self.dhcpcd = None
        self.clear_l3addrs()


class Konnektor:
    def __init__(self, interfaces):
        self.interfaces = []
        for interface in interfaces:
            self.interfaces += [ Link(interface) ]

    def loop(self):
        # the main loop
        while True:
            s = 1
            try:
                for interface in self.interfaces:
                    if s == 1 and interface.is_active():
                        interface.up()
                        s = 0
                    else:
                        interface.down()
            except subprocess.CalledProcessError:
                pass
            time.sleep(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        k = Konnektor(sys.argv[1:])
        k.loop()
    else:
        print(description.replace(": konnektor.py", ": " + sys.argv[0])[1:][:-1])

