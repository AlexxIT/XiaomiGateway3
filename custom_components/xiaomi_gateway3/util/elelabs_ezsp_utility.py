# Copyright 2020 Elelabs International Limited

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import binascii
import io
import socket
import time

from xmodem import XMODEM


# Maximum untouched utility with fix only serial class from pyserial to TCP
# https://github.com/Elelabs/elelabs-zigbee-ezsp-utility
class serial:
    PARITY_NONE = None
    STOPBITS_ONE = None

    class Serial:
        def __init__(self, port, **kwargs):
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.settimeout(5)
            self.s.connect(port)

        def flushInput(self):
            pass

        def read(self, size: int = 1):
            try:
                return self.s.recv(size)
            except:
                return b''

        def readline(self):
            raw = b''
            while True:
                c = self.read()
                raw += c
                if c == b'\n' or c == b'':
                    break
            return raw

        def write(self, data: bytes):
            self.s.send(data)

        def close(self):
            self.s.close()


class AdapterModeProbeStatus:
    NORMAL = 0
    BOOTLOADER = 1
    ERROR = 2


class SerialInterface:
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate

    def open(self):
        try:
            self.serial = serial.Serial(port=self.port,
                                        baudrate=self.baudrate,
                                        parity=serial.PARITY_NONE,
                                        stopbits=serial.STOPBITS_ONE,
                                        xonxoff=True,
                                        timeout=3)
        except Exception as e:
            raise Exception("PORT ERROR: %s" % str(e))

    def close(self):
        self.serial.close()


class AshProtocolInterface:
    FLAG_BYTE = b'\x7E'
    RANDOMIZE_START = 0x42
    RANDOMIZE_SEQ = 0xB8
    RSTACK_FRAME_CMD = b'\x1A\xC0\x38\xBC\x7E'
    RSTACK_FRAME_ACK = b'\x1A\xC1\x02\x0B\x0A\x52\x7E'

    def __init__(self, serial, config, logger):
        self.logger = logger
        self.config = config
        self.serial = serial

        self.ackNum = 0
        self.frmNum = 0

    def dataRandomize(self, frame):
        rand = self.RANDOMIZE_START
        out = bytearray()
        for x in frame:
            out += bytearray([x ^ rand])
            if rand % 2:
                rand = (rand >> 1) ^ self.RANDOMIZE_SEQ
            else:
                rand = rand >> 1
        return out

    def ashFrameBuilder(self, ezsp_frame):
        ash_frame = bytearray()
        # Control byte
        ash_frame += bytearray([(((self.ackNum << 0) & 0xFF) | (
                ((self.frmNum % 8) << 4) & 0xFF)) & 0xFF])
        self.ackNum = (self.ackNum + 1) % 8
        self.frmNum = (self.frmNum + 1) % 8
        ash_frame += self.dataRandomize(ezsp_frame)
        crc = binascii.crc_hqx(ash_frame, 0xFFFF)
        ash_frame += bytearray([crc >> 8, crc & 0xFF])
        ash_frame = self.replaceReservedBytes(ash_frame)
        ash_frame += self.FLAG_BYTE
        if self.config.dlevel == 'ASH':
            self.logger.debug('[ ASH  REQUEST ] ' + ' '.join(
                format(x, '02x') for x in ash_frame))
        return ash_frame

    def revertEscapedBytes(self, msg):
        msg = msg.replace(b'\x7d\x5d', b'\x7d')
        msg = msg.replace(b'\x7d\x5e', b'\x7e')
        msg = msg.replace(b'\x7d\x31', b'\x11')
        msg = msg.replace(b'\x7d\x33', b'\x13')
        msg = msg.replace(b'\x7d\x38', b'\x18')
        msg = msg.replace(b'\x7d\x3a', b'\x1a')
        return msg

    def replaceReservedBytes(self, msg):
        msg = msg.replace(b'\x7d', b'\x7d\x5d')
        msg = msg.replace(b'\x7e', b'\x7d\x5e')
        msg = msg.replace(b'\x11', b'\x7d\x31')
        msg = msg.replace(b'\x13', b'\x7d\x33')
        msg = msg.replace(b'\x18', b'\x7d\x38')
        msg = msg.replace(b'\x1a', b'\x7d\x3a')
        return msg

    def getResponse(self, applyRandomize=False):
        timeout = time.time() + 3
        msg = bytearray()

        receivedbyte = None

        while (time.time() < timeout) and (receivedbyte != self.FLAG_BYTE):
            receivedbyte = self.serial.read()
            msg += receivedbyte

        if len(msg) == 0:
            return -1, None, None

        msg = self.revertEscapedBytes(msg)

        if self.config.dlevel == 'ASH':
            self.logger.debug(
                '[ ASH RESPONSE ] ' + ' '.join(format(x, '02x') for x in msg))

        if applyRandomize:
            msg_parsed = self.dataRandomize(bytearray(msg[1:-3]))
            if self.config.dlevel == 'ASH' or self.config.dlevel == 'EZSP':
                self.logger.debug('[ EZSP RESPONSE ] ' + ' '.join(
                    format(x, '02x') for x in msg_parsed))
            return 0, msg, msg_parsed
        else:
            return 0, msg

    def sendResetFrame(self):
        self.serial.flushInput()
        self.logger.debug('RESET FRAME')
        if self.config.dlevel == 'ASH':
            self.logger.debug('[ ASH  REQUEST ] ' + ' '.join(
                format(x, '02x') for x in self.RSTACK_FRAME_CMD))
        self.serial.write(self.RSTACK_FRAME_CMD)
        status, response = self.getResponse()

        if status:
            return status

        if not (self.RSTACK_FRAME_ACK in response):
            return -1

        return 0

    def sendAck(self, ackNum):
        ack = bytearray([ackNum & 0x07 | 0x80])
        crc = binascii.crc_hqx(ack, 0xFFFF)
        ack += bytearray([crc >> 8, crc & 0xFF])
        ack = self.replaceReservedBytes(ack)
        ack += self.FLAG_BYTE

        if self.config.dlevel == 'ASH':
            self.logger.debug(
                '[ ASH ACK ] ' + ' '.join(format(x, '02x') for x in ack))
        self.serial.write(ack)

    def sendAshCommand(self, ezspFrame):
        ash_frame = self.ashFrameBuilder(ezspFrame)
        self.serial.flushInput()
        self.serial.write(ash_frame)
        status, ash_response, ezsp_response = self.getResponse(True)
        if status:
            return status, None

        self.sendAck(ash_response[0])
        return 0, ezsp_response


class EzspProtocolInterface:
    def __init__(self, serial, config, logger):
        self.logger = logger
        self.config = config

        self.INITIAL_EZSP_VERSION = 4

        self.VERSION = b'\x00'
        self.GET_VALUE = b'\xAA'
        self.GET_MFG_TOKEN = b'\x0B'
        self.LAUNCH_STANDALONE_BOOTLOADER = b'\x8F'

        self.EZSP_VALUE_VERSION_INFO = 0x11
        self.EZSP_MFG_STRING = 0x01
        self.EZSP_MFG_BOARD_NAME = 0x02
        self.STANDALONE_BOOTLOADER_NORMAL_MODE = 1

        self.ezspVersion = self.INITIAL_EZSP_VERSION
        self.sequenceNum = 0
        self.ash = AshProtocolInterface(serial, config, logger)

    def ezspFrameBuilder(self, command):
        ezsp_frame = bytearray()

        # Sequence byte
        ezsp_frame += bytearray([self.sequenceNum])
        self.sequenceNum = (self.sequenceNum + 1) % 255
        ezsp_frame += b'\x00'
        if self.ezspVersion >= 5:
            # Legacy frame ID - always 0xFF
            ezsp_frame += b'\xFF'
            # Extended frame control
            ezsp_frame += b'\x00'

        ezsp_frame = ezsp_frame + command

        if self.ezspVersion >= 8:
            ezsp_frame[2] = 0x01
            ezsp_frame[3] = command[0] & 0xFF  # LSB
            ezsp_frame[4] = command[0] >> 8  # MSB

        if self.config.dlevel == 'ASH' or self.config.dlevel == 'EZSP':
            self.logger.debug('[ EZSP  REQUEST ] ' + ' '.join(
                format(x, '02x') for x in ezsp_frame))
        return ezsp_frame

    def sendEzspCommand(self, commandData, commandName=''):
        self.logger.debug(commandName)
        status, response = self.ash.sendAshCommand(
            self.ezspFrameBuilder(commandData))
        if status:
            raise Exception("sendAshCommand status error: %d" % status)

        return response

    def sendVersion(self, desiredProtocolVersion):
        resp = self.sendEzspCommand(
            self.VERSION + bytearray([desiredProtocolVersion]),
            'sendVersion: V%d' % desiredProtocolVersion)
        return resp[3]  # protocolVersion

    def getValue(self, valueId, valueIdName):
        resp = self.sendEzspCommand(self.GET_VALUE + bytearray([valueId]),
                                    'getValue: %s' % valueIdName)
        status = resp[5]
        valueLength = resp[6]
        valueArray = resp[7:]
        return status, valueLength, valueArray

    def getMfgToken(self, tokenId, tokenIdName):
        resp = self.sendEzspCommand(self.GET_MFG_TOKEN + bytearray([tokenId]),
                                    'getMfgToken: %s' % tokenIdName)
        tokenDataLength = resp[5]
        tokenData = resp[6:]
        return tokenDataLength, tokenData

    def launchStandaloneBootloader(self, mode, modeName):
        resp = self.sendEzspCommand(
            self.LAUNCH_STANDALONE_BOOTLOADER + bytearray([mode]),
            'launchStandaloneBootloader: %s' % modeName)
        status = resp[5]
        return status

    def initEzspProtocol(self):
        ash_status = self.ash.sendResetFrame()
        if ash_status:
            return ash_status

        self.ezspVersion = self.sendVersion(self.INITIAL_EZSP_VERSION)
        self.logger.debug("EZSP v%d detected" % self.ezspVersion)
        if (self.ezspVersion != self.INITIAL_EZSP_VERSION):
            self.sendVersion(self.ezspVersion)

        return 0


class ElelabsUtilities:
    def __init__(self, config, logger):
        self.logger = logger
        self.config = config

    def probe(self):
        serialInterface = SerialInterface(self.config.port,
                                          self.config.baudrate)
        serialInterface.open()

        ezsp = EzspProtocolInterface(serialInterface.serial, self.config,
                                     self.logger)
        ezsp_status = ezsp.initEzspProtocol()
        if ezsp_status == 0:
            status, value_length, value_array = ezsp.getValue(
                ezsp.EZSP_VALUE_VERSION_INFO, "EZSP_VALUE_VERSION_INFO")
            if (status == 0):
                firmware_version = str(value_array[2]) + '.' + str(
                    value_array[3]) + '.' + str(value_array[4]) + '-' + str(
                    value_array[0])
            else:
                self.logger.info('EZSP status returned %d' % status)

            token_data_length, token_data = ezsp.getMfgToken(
                ezsp.EZSP_MFG_STRING, "EZSP_MFG_STRING")
            if token_data.decode("ascii", "ignore") == "Elelabs":
                token_data_length, token_data = ezsp.getMfgToken(
                    ezsp.EZSP_MFG_BOARD_NAME, "EZSP_MFG_BOARD_NAME")
                adapter_name = token_data.decode("ascii", "ignore")

                self.logger.info("Elelabs adapter detected:")
                self.logger.info("Adapter: %s" % adapter_name)
            else:
                adapter_name = None
                self.logger.info("Generic EZSP adapter detected:")

            self.logger.info("Firmware: %s" % firmware_version)
            self.logger.info("EZSP v%d" % ezsp.ezspVersion)

            serialInterface.close()
            return AdapterModeProbeStatus.NORMAL, ezsp.ezspVersion, firmware_version, adapter_name
        else:
            if self.config.baudrate != 115200:
                serialInterface.close()
                time.sleep(1)
                serialInterface = SerialInterface(self.config.port, 115200)
                serialInterface.open()

            # check if allready in bootloader mode
            serialInterface.serial.write(b'\x0A')
            first_line = serialInterface.serial.readline()  # read blank line
            if len(first_line) == 0:
                # timeout
                serialInterface.close()
                self.logger.info(
                    "Couldn't communicate with the adapter in normal or in bootloader modes")
                return AdapterModeProbeStatus.ERROR, None, None, None

            btl_info = serialInterface.serial.readline()  # read Gecko BTL version or blank line

            self.logger.info("EZSP adapter in bootloader mode detected:")
            self.logger.info(btl_info.decode("ascii", "ignore")[
                             :-2])  # show Bootloader version
            serialInterface.close()
            return AdapterModeProbeStatus.BOOTLOADER, None, None, None

    def restart(self, mode):
        adapter_status, ezsp_version, firmware_version, adapter_name = self.probe()
        if adapter_status == AdapterModeProbeStatus.NORMAL:
            if mode == 'btl':
                serialInterface = SerialInterface(self.config.port,
                                                  self.config.baudrate)
                serialInterface.open()

                self.logger.info("Launch in bootloader mode")
                ezsp = EzspProtocolInterface(serialInterface.serial,
                                             self.config, self.logger)
                ezsp_status = ezsp.initEzspProtocol()
                status = ezsp.launchStandaloneBootloader(
                    ezsp.STANDALONE_BOOTLOADER_NORMAL_MODE,
                    "STANDALONE_BOOTLOADER_NORMAL_MODE")
                if status:
                    serialInterface.close()
                    self.logger.critical(
                        "Error launching the adapter in bootloader mode")
                    return -1

                serialInterface.close()
                # wait for reboot
                time.sleep(2)

                adapter_status, ezsp_version, firmware_version, adapter_name = self.probe()
                if adapter_status == AdapterModeProbeStatus.BOOTLOADER:
                    return 0
                else:
                    return -1
            else:
                self.logger.info(
                    "Allready in EZSP normal mode. No need to restart")
                return 0
        elif adapter_status == AdapterModeProbeStatus.BOOTLOADER:
            if mode == 'btl':
                self.logger.info(
                    "Allready in bootloader mode. No need to restart")
                return 0
            else:
                serialInterface = SerialInterface(self.config.port, 115200)
                serialInterface.open()

                self.logger.info("Launch in EZSP normal mode")

                # Send Reboot
                serialInterface.serial.write(b'2')
                serialInterface.close()

                # wait for reboot
                time.sleep(2)

                adapter_status, ezsp_version, firmware_version, adapter_name = self.probe()
                if adapter_status == AdapterModeProbeStatus.NORMAL:
                    return 0
                else:
                    return -1

    def flash(self, filename):
        # STATIC FUNCTIONS
        def getc(size, timeout=1):
            read_data = self.serialInterface.serial.read(size)
            return read_data

        def putc(data, timeout=1):
            self.currentPacket += 1
            if (self.currentPacket % 20) == 0:
                print('.', end='')
            if (self.currentPacket % 100) == 0:
                print('')
            self.serialInterface.serial.write(data)
            time.sleep(0.001)

        # if not (".gbl" in filename) and not (".ebl" in filename):
        #     self.logger.critical(
        #         'Aborted! Gecko bootloader accepts .gbl or .ebl images only.')
        #     return

        if self.restart("btl"):
            self.logger.critical(
                "EZSP adapter not in the bootloader mode. Can't perform update procedure")

        self.serialInterface = SerialInterface(self.config.port, 115200)
        self.serialInterface.open()
        # Enter '1' to initialize X-MODEM mode
        self.serialInterface.serial.write(b'\x0A')
        self.serialInterface.serial.write(b'1')
        time.sleep(1)
        self.serialInterface.serial.readline()  # BL > 1
        self.serialInterface.serial.readline()  # begin upload

        self.logger.info(
            'Successfully restarted into X-MODEM mode! Starting upload of the new firmware... DO NOT INTERRUPT(!)')

        self.currentPacket = 0
        # Wait for char 'C'
        success = False
        start_time = time.time()
        while time.time() - start_time < 10:
            if self.serialInterface.serial.read() == b'C':
                success = True
                if time.time() - start_time > 5:
                    break
        if not success:
            self.logger.info(
                'Failed to restart into bootloader mode. Please see users guide.')
            return

        # Start XMODEM transaction
        modem = XMODEM(getc, putc)
        # stream = open(filename, 'rb')
        stream = io.BytesIO(filename)
        sentcheck = modem.send(stream)

        print('')
        if sentcheck:
            self.logger.info('Firmware upload complete')
        else:
            self.logger.critical(
                'Firmware upload failed. Please try a correct firmware image or restart in normal mode.')
            return
        self.logger.info('Rebooting NCP...')
        # Wait for restart
        time.sleep(4)
        # Send Reboot into App-Code command
        self.serialInterface.serial.write(b'2')
        self.serialInterface.close()
        time.sleep(2)
        return self.probe()

    def ele_update(self, new_version):
        adapter_status, ezsp_version, firmware_version, adapter_name = self.probe()
        if adapter_status == AdapterModeProbeStatus.NORMAL:
            if adapter_name == None:
                self.logger.critical(
                    "No Elelabs product detected.\r\nUse 'flash' utility for generic EZSP products.\r\nContact info@elelabs.com if you see this meesage for original Elelabs product")
                return

            if new_version == 'v6' and ezsp_version == 6:
                self.logger.info(
                    "Elelabs product is operating EZSP protocol v%d. No need to update to %s" % (
                        ezsp_version, new_version))
                return

            if new_version == 'v8' and ezsp_version == 8:
                self.logger.info(
                    "Elelabs product is operating EZSP protocol v%d. No need to update to %s" % (
                        ezsp_version, new_version))
                return

            if adapter_name == "ELR023" or adapter_name == "ELU013":
                if new_version == 'v6':
                    self.flash("data/ELX0X3_MG13_6.0.3_ezsp_v6.gbl")
                elif new_version == 'v8':
                    self.flash("data/ELX0X3_MG13_6.7.0_ezsp_v8.gbl")
                else:
                    self.logger.critical("Unknown EZSP version")
            elif adapter_name == "ELR022" or adapter_name == "ELU012":
                self.logger.critical(
                    "TODO!. Contact Elelabs at info@elelabs.com")
            elif adapter_name == "EZBPIS" or adapter_name == "EZBUSBA":
                self.logger.critical(
                    "TODO!. Contact Elelabs at info@elelabs.com")
            else:
                self.logger.critical(
                    "Unknown Elelabs product %s detected.\r\nContact info@elelabs.com if you see this meesage for original Elelabs product" % adapter_name)
        elif adapter_status == AdapterModeProbeStatus.BOOTLOADER:
            self.logger.critical(
                "The product not in the normal EZSP mode.\r\n'restart' into normal mode or use 'flash' utility instead")
        else:
            self.logger.critical("No upgradable device found")
