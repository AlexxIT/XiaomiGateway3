import json

from custom_components.xiaomi_gateway3.core import utils


def test_ble_normal_message():
    raw = b'[20201207 09:07:48] [D] ot_agent_recv_handler_one(): fd:11, msg:{"method":"_async.ble_event","params":{"dev":{"did":"blt.3.iambledevice0","mac":"AA:BB:CC:DD:EE:FF","pdid":426},"evt":[{"eid":4102,"edata":"a801"}],"frmCnt":19,"gwts":1607321268},"id":123456} length:191 bytes'
    assert len([json.loads(item) for item in utils.extract_jsons(raw)]) == 1


def test_ble_concat_messages():
    """Two concatenated messages"""
    raw = b'[20201101 23:25:11] [D] ot_agent_recv_handler_one(): fd:11, msg:{"method":"_async.ble_event","params":{"dev":{"did":"blt.3.iambledevice0","mac":"AA:BB:CC:DD:EE:FF","pdid":2038},"evt":[{"eid":15,"edata":"640000"}],"frmCnt":100,"gwts":1604262311},"id":1234567}{"method":"local.query_status","params":"","id":4422874} length:250 bytes'
    assert len([json.loads(item) for item in utils.extract_jsons(raw)]) == 2


def test_ble_overflow_message():
    """One overflow message"""
    raw = b'[20201124 19:41:24] [D] ot_agent_recv_handler_one(): fd:10, msg:{"method":"_async.ble_event","params":{"dev":{"did":"blt.3.iambledevice0","mac":"AA:BB:CC:DD:EE:FF","pdid":1398},"evt":[{"eid":4106,"edata":"64"}],"frmCnt":184,"gwts":1606236083},"id":1234567}"lumi.sensor_motion.aq2","params":[],"sid":"lumi.1234567890123456","id":7817979}{"method":"props","model":"lumi.sensor_motion.aq2","params":{"no_motion_1800":0},"sid":"lumi.1234567890123456","id":7817985} length:192 bytes'
    assert len([json.loads(item) for item in utils.extract_jsons(raw)]) == 1


def test_ble_147_miio_func():
    raw = b'\x1b[0;32m2020:12:05:01:47:03.521 [D] miio_client_func: ot_agent_recv_handler_one(): fd:9, msg:{"method":"_async.ble_event","params":{"dev":{"did":"blt.3.iambledevice0","mac":"AA:BB:CC:DD:EE:FF","pdid":426},"evt":[{"eid":4100,"edata":"ea00"}],"frmCnt":44,"gwts":1607104023},"id":1234} length:189 bytes\x1b[0m'
    assert len([json.loads(item) for item in utils.extract_jsons(raw)]) == 1


def test_ble_147_miio_rpc():
    raw = b'\x1b[0;32m2020:12:05:01:47:03.521 [D] miio_client_rpc: call={"method":"_async.ble_event","params":{"dev":{"did":"blt.3.iambledevice0","mac":"AA:BB:CC:DD:EE:FF","pdid":426},"evt":[{"eid":4100,"edata":"ea00"}],"frmCnt":44,"gwts":1607104023},"id":1234}\x1b[0m'
    assert len([json.loads(item) for item in utils.extract_jsons(raw)]) == 1


def test_ble_147_ots():
    raw = b'\x1b[0;32m2020:12:05:01:47:03.530 [D] ots: ots_up_rpc_delegate_out_cb(), 289, {"method":"_async.ble_event","params":{"dev":{"did":"blt.3.iambledevice0","mac":"AA:BB:CC:DD:EE:FF","pdid":426},"evt":[{"eid":4100,"edata":"ea00"}],"frmCnt":44,"gwts":1607104023},"id":1234}\x1b[0m'
    assert len([json.loads(item) for item in utils.extract_jsons(raw)]) == 1
