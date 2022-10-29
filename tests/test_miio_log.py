import json


def test_gw_heartbeat():
    raw = b'{"method":"event.gw.heartbeat","params":[{"free_mem":11872,"ip":"192.168.1.123","load_avg":"1.24|1.39|1.38|4\\/88|720","rssi":58,"run_time":358537,"ssid":"WiFi"}],"id":151593}'
    p = json.loads(raw)
    assert p["params"][0]["free_mem"] == 11872


def test_properties_changed():
    raw = b'{"method":"properties_changed","params":[{"did":"<10 numb>","siid":2,"piid":1,"value":true}],"id":152814}'
    p = json.loads(raw)
    assert p["params"][0]["siid"] == 2


def test_ble_event():
    raw = b'{"method":"_async.ble_event","params":{"dev":{"did":"blt.3.<alphanum>","mac":"<mac>","pdid":2038},"evt":[{"eid":4119,"edata":"00000000"}],"frmCnt":233,"gwts":1634192427},"id":151482}'
    p = json.loads(raw)
    assert p["params"]["dev"]["pdid"] == 2038


def test_miot_event():
    # https://github.com/AlexxIT/XiaomiGateway3/issues/689#issuecomment-1066048885
    raw = b'{"method":"event_occured","params":{"did":"<10 numb>","siid":8,"eiid":1,"tid":44,"ts":1647158504,"arguments":[]},"id":548629}'
    p = json.loads(raw)
    assert p["params"]["siid"] == 8
