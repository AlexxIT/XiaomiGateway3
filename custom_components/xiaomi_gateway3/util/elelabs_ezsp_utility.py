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

# https://github.com/Elelabs/elelabs-zigbee-ezsp-utility
import binascii
import time


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
            return 0, msg, None

    def sendResetFrame(self):
        self.serial.flushInput()
        self.logger.debug('RESET FRAME')
        if self.config.dlevel == 'ASH':
            self.logger.debug('[ ASH  REQUEST ] ' + ' '.join(
                format(x, '02x') for x in self.RSTACK_FRAME_CMD))
        self.serial.write(self.RSTACK_FRAME_CMD)
        status, ash_response, ezsp_response = self.getResponse()

        if status:
            return status

        if not (self.RSTACK_FRAME_ACK in ash_response):
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
