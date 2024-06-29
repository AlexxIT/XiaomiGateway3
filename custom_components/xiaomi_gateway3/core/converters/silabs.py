import logging

from zigpy.zcl import Cluster
from zigpy.zcl.foundation import (
    DATA_TYPES,
    GENERAL_COMMANDS,
    CommandSchema,
    TypeValue,
    ZCLCommandDef,
    ZCLHeader,
)
from zigpy.zcl.foundation import GeneralCommand
from zigpy.zdo import ZDO
from zigpy.zdo.types import (
    ZDOCmd,
    Neighbors,
    NodeDescriptor,
    SizePrefixedSimpleDescriptor,
    Status as ZDOStatus,
)

_LOGGER = logging.getLogger(__name__)

CLUSTERS = {}


def decode(payload: dict) -> dict | None:
    try:
        cluster_id = int(payload["clusterId"], 0)
        data = bytes.fromhex(payload["APSPlayload"][2:])  # 0xAABBCCDDEEFF

        if payload.get("sourceEndpoint") == "0x00":
            return zdo_deserialize(cluster_id, data)

        if cluster_id == 0 and (basic := xiaomi_deserialize(data)):
            return basic

        return zcl_deserialize(cluster_id, data)
    except Exception as e:
        _LOGGER.debug("Error while parsing zigbee", exc_info=e)
        return None


def zdo_deserialize(cluster_id: int, payload: bytes):
    if (zdo := CLUSTERS.get("zdo")) is None:
        zdo = CLUSTERS["zdo"] = ZDO(None)

    hdr, args = zdo.deserialize(cluster_id, payload)
    if hdr.command_id == ZDOCmd.Active_EP_rsp:
        return {
            "zdo_command": hdr.command_id.name,
            "status": str(args[0]),
            "endpoints": args[2],
        }
    elif hdr.command_id == ZDOCmd.Simple_Desc_rsp:
        desc: SizePrefixedSimpleDescriptor = args[2]
        return {
            "zdo_command": hdr.command_id.name,
            "status": str(args[0]),
            "device_type": desc.device_type,
            "device_version": desc.device_version,
            "endpoint": desc.endpoint,
            "input_clusters": desc.input_clusters,
            "output_clusters": desc.output_clusters,
            "profile": desc.profile,
        }
    elif hdr.command_id == ZDOCmd.Node_Desc_rsp:
        desc: NodeDescriptor = args[2]
        return {
            "zdo_command": hdr.command_id.name,
            "status": str(args[0]),
            "is_mains_powered": desc.is_mains_powered,
            "logical_type": str(desc.logical_type),
            "manufacturer_code": desc.manufacturer_code,
        }
    elif hdr.command_id in (ZDOCmd.Bind_rsp, ZDOCmd.Mgmt_Leave_rsp):
        return {
            "zdo_command": hdr.command_id.name,
            "status": str(args[0]),
        }
    elif hdr.command_id in (ZDOCmd.Node_Desc_req, ZDOCmd.Active_EP_req):
        return {"zdo_command": hdr.command_id.name}
    elif hdr.command_id == ZDOCmd.Simple_Desc_req:
        return {
            "zdo_command": hdr.command_id.name,
            "endpoint": args[0],
        }
    elif hdr.command_id == ZDOCmd.Bind_req:
        return {
            "zdo_command": hdr.command_id.name,
            "src_addr": args[0],
            "src_endpoint": args[1],
            "cluster": args[2],
            "dst_addr": args[3],
        }
    elif hdr.command_id == ZDOCmd.IEEE_addr_rsp:
        return {
            "zdo_command": hdr.command_id.name,
            "status": args[0],
            "ieee": args[1],
            "nwk": args[2],
        }
    elif hdr.command_id == ZDOCmd.Mgmt_Leave_req:
        return {
            "zdo_command": hdr.command_id.name,
            "ieee": args[0],
        }
    elif hdr.command_id == ZDOCmd.Mgmt_NWK_Update_rsp:
        return {
            "zdo_command": hdr.command_id.name,
            "status": args[0],
            "channels": args[1],
            "total": args[2],
            "failures": args[3],
            "energy": args[4],
        }
    elif hdr.command_id == ZDOCmd.NWK_addr_rsp:
        return {
            "zdo_command": hdr.command_id.name,
            "status": args[0].name,
            "ieee": str(args[1]),
            "nwk": str(args[2]),
        }
    elif hdr.command_id == ZDOCmd.Mgmt_Lqi_req:
        # https://docs.silabs.com/zigbee/6.5/af_v2/group-zdo
        return {"zdo_command": hdr.command_id.name, "start_index": args[0]}
    elif hdr.command_id == ZDOCmd.Mgmt_Lqi_rsp:
        assert args[0] == ZDOStatus.SUCCESS, args  # status
        neighbors: Neighbors = args[1]
        items = [
            {
                "ieee": str(i.ieee),
                "nwk": str(i.nwk).lower(),
                "device_type": i.device_type.name,
                "relationship": i.relationship.name,
                "depth": int(i.depth),
                "lqi": int(i.lqi),
            }
            for i in neighbors.NeighborTableList
        ]
        return {
            "zdo_command": hdr.command_id.name,
            "entries": int(neighbors.Entries),
            "start_index": int(neighbors.StartIndex),
            "neighbors": items,
        }
    elif hdr.command_id == ZDOCmd.Mgmt_Rtg_rsp:
        return {
            "zdo_command": hdr.command_id.name,
            "status": args[0],
            "routes": args[1],
        }
    else:
        raise NotImplemented


def zcl_deserialize(cluster_id: int, data: bytes) -> dict:
    """Decode Silabs Z3 GatewayHost MQTT message using zigpy library. Supports
    ZDO payload and ZCL payload.
    """
    if not (cluster := CLUSTERS.get(cluster_id)):
        # noinspection PyTypeChecker
        cluster = CLUSTERS[cluster_id] = Cluster.from_id(None, cluster_id)
        cluster._log = lambda *_, **__: None

    try:
        hdr, resp = cluster.deserialize(data)
    except ValueError as e:
        return {"cluster_id": cluster_id, "error": str(e)}
    except KeyError as e:
        return {"cluster_id": cluster_id, "error": f"Key error: {e}"}

    payload: dict = {"cluster": cluster.ep_attribute} if cluster.ep_attribute else {}

    if hdr.frame_control.is_general:
        payload["general_command_id"] = hdr.command_id
        fields = resp.as_dict()

        if hdr.command_id == GeneralCommand.Read_Attributes:
            payload.update(fields)
        elif hdr.command_id == GeneralCommand.Report_Attributes:
            for attr in fields["attribute_reports"]:
                payload[attr.attrid] = value_decode(attr.value)
        elif hdr.command_id == GeneralCommand.Write_Attributes:
            for attr in fields["attributes"]:
                payload[attr.attrid] = value_decode(attr.value)
        elif hdr.command_id == GeneralCommand.Read_Attributes_rsp:
            for attr in fields["status_records"]:
                payload[attr.attrid] = value_decode(attr.value)
        elif hdr.command_id == GeneralCommand.Write_Attributes_rsp:
            for attr in fields["status_records"]:
                payload[attr.attrid] = value_decode(attr.status)
        else:
            payload["header"] = hdr
            payload["response"] = resp

    elif hdr.frame_control.is_cluster:
        payload["cluster_command_id"] = hdr.command_id
        if isinstance(resp, CommandSchema):
            payload["value"] = {k: value_decode(v) for k, v in resp.as_dict().items()}
        else:
            payload["value"] = resp

    else:
        payload = {"header": hdr, "cluster": cluster, "response": resp}

    return payload


def value_decode(value) -> bool | int | float | bytes | str:
    if isinstance(value, TypeValue):
        return value_decode(value.value)
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value)
    if isinstance(value, bytes):
        return bytes(value)
    if isinstance(value, str):
        return str(value)
    return value


def xiaomi_deserialize(data: bytes) -> dict | None:
    hdr, data = ZCLHeader.deserialize(data)
    if (
        not hdr.frame_control.is_general
        or hdr.command_id != GeneralCommand.Report_Attributes
    ):
        return None

    payload = {
        "cluster": "basic",
        "general_command_id": hdr.command_id,
    }

    while len(data) >= 3:
        attr_id = int.from_bytes(data[:2], "little")
        if attr_id == 0xFF01:
            if int(data[2]) != 0x42:
                return None

            data = data[4:]  # skip data length (sometimes wrong)
            value = {}
            while len(data) > 1:
                sub_id = int(data[0])
                sub_value, data = TypeValue.deserialize(data[1:])
                value[sub_id] = value_decode(sub_value)
        else:
            sub_value, data = TypeValue.deserialize(data[2:])
            value = value_decode(sub_value)

        payload[attr_id] = value

    return payload


def get_type_id(cluster_id: int, attr_id: int) -> int:
    attr = XCluster(cluster_id).attributes[attr_id]
    return next(k for k, v in DATA_TYPES.items() if issubclass(attr.type, v[1]))


def attr_encode(type_id: int, value: int) -> bytes:
    cls = DATA_TYPES[type_id][1]
    return cls(value).serialize()


def zcl_on_off(nwk: str, ep: int, value: bool) -> list:
    """Generate Silabs Z3 command (cluster 6)."""
    value = "on" if value else "off"
    return [{"commandcli": f"zcl on-off {value}"}, {"commandcli": f"send {nwk} 1 {ep}"}]


# zcl level-control mv-to-level [level:1] [transitionTime:2] [optionMask:1] [optionOverride:1]
def zcl_level(nwk: str, ep: int, br: int, tr: float) -> list:
    """Generate Silabs Z3 command (cluster 8)."""
    tr = int(tr * 10.0)  # zcl format - tenths of a seconds
    return [
        {"commandcli": f"zcl level-control o-mv-to-level {br} {tr}"},
        {"commandcli": f"send {nwk} 1 {ep}"},
    ]


def zcl_color_temp(nwk: str, ep: int, ct: int, tr: float) -> list:
    """Generate Silabs Z3 command (cluster 0x0300)."""
    tr = int(tr * 10.0)  # zcl format - tenths of a seconds
    return [
        {"commandcli": f"zcl color-control movetocolortemp {ct} {tr} 0 0"},
        {"commandcli": f"send {nwk} 1 {ep}"},
    ]


def zcl_color_hs(nwk: str, ep: int, h: int, s: int, tr: float) -> list:
    """Generate Silabs Z3 command (cluster 0x0300)."""
    tr = int(tr * 10.0)  # zcl format - tenths of a seconds
    return [
        {"commandcli": f"zcl color-control movetohueandsat {h} {s} {tr} 0 0"},
        {"commandcli": f"send {nwk} 1 {ep}"},
    ]


# noinspection PyProtectedMember
class XCluster:
    cluster: Cluster

    def __init__(self, cluster_id: int):
        self.cluster = Cluster._registry[cluster_id]

    @property
    def id(self):
        return self.cluster.cluster_id

    @property
    def attributes(self):
        return self.cluster.attributes

    def command(self, command_id: int, *args, **kwargs) -> bytes:
        command = self.cluster.server_commands[command_id]
        return self.request(False, command, *args, **kwargs)

    def read_attrs(self, *args) -> bytes:
        command = GENERAL_COMMANDS[GeneralCommand.Read_Attributes]
        return self.request(True, command, args)

    def request(self, general: bool, command: ZCLCommandDef, *args, **kwargs) -> bytes:
        # noinspection PyArgumentList
        hdr, request = self.cluster._create_request(
            None,  # self
            general=general,
            command_id=command.id,
            schema=command.schema,
            manufacturer=None,
            tsn=0,  # will be owerwriten by silabs software
            disable_default_response=True,  # silabs uses this value by default
            direction=0,  # can't use const, because it is wrong on old Hass
            args=args,  # command args
            kwargs=kwargs,  # command kwargs
        )

        # noinspection PyUnresolvedReferences
        return hdr.serialize() + request.serialize()


def zcl_command(
    nwk: str, ep: int, cluster_id: str | int, command_id: int, *args
) -> list[dict]:
    raw = XCluster(cluster_id).command(command_id, *args).hex()
    return [
        {"commandcli": f"raw {cluster_id} {{{raw}}}"},
        {"commandcli": f"send {nwk} 1 {ep}"},
    ]


# zcl global read [cluster:2] [attributeId:2]
def zcl_read(nwk: str, ep: int, cluster_id: int, attr_id: int, mfg: int = None) -> list:
    """Generate Silabs Z3 read attribute command. Support multiple attrs."""
    cli = f"zcl global read {cluster_id} {attr_id}"
    commands = [{"commandcli": cli}, {"commandcli": f"send {nwk} 1 {ep}"}]
    return [{"commandcli": f"zcl mfg-code {mfg}"}] + commands if mfg else commands


def optimize_read(commands: list[dict]) -> bool:
    """Collect all similar zcl global read to one zigbee message."""
    read: dict[tuple, list] = {}
    mfg = cluster_id = attr_id = None
    optimize = False

    for item in commands:
        cli: str = item["commandcli"]
        if cli.startswith("zcl mfg-code"):
            words = cli.split(" ")
            mfg = words[2]
        elif cli.startswith("zcl global read"):
            words = cli.split(" ")
            cluster_id = words[3]
            attr_id = words[4]
        elif cli.startswith("send") and cluster_id:
            index = (cli, cluster_id, mfg)
            if index in read:
                read[index].append(attr_id)
                optimize = True
            else:
                read[index] = [attr_id]
            mfg = cluster_id = attr_id = None
        else:
            return False

    if not optimize:
        return False

    # rebuild commands list
    commands.clear()

    for index, attrs in read.items():
        cli, cluster_id, mfg = index
        if mfg:
            commands.append({"commandcli": f"zcl mfg-code {mfg}"})
        if len(attrs) > 1:
            raw = "".join(int(a).to_bytes(2, "little").hex() for a in attrs)
            commands.append({"commandcli": f"raw {cluster_id} {{100000{raw}}}"})
        else:
            commands.append({"commandcli": f"zcl global read {cluster_id} {attrs[0]}"})
        commands.append({"commandcli": cli})

    return True


# zcl global write [cluster:2] [attributeId:2] [type:4] [data:-1]
def zcl_write(
    nwk: str,
    ep: int,
    cluster_id: int,
    attr_id: int,
    value: int,
    *,
    type_id: int = None,
    mfg: int = None,
) -> list:
    """Generate Silabs Z3 write attribute command."""
    if type_id is None:
        type_id = get_type_id(cluster_id, attr_id)

    data = attr_encode(type_id, value).hex()

    pre = [{"commandcli": f"zcl mfg-code {mfg}"}] if mfg is not None else []
    cli = f"zcl global write {cluster_id} {attr_id} {type_id} {{{data}}}"
    return pre + [{"commandcli": cli}, {"commandcli": f"send {nwk} 1 {ep}"}]


# zdo bind [destination:2] [source Endpoint:1] [destEndpoint:1] [cluster:2] [remoteEUI64:8] [destEUI64:8]
def zdo_bind(nwk: str, ep: int, cluster_id: int, src: str, dst: str) -> list:
    """Generate Silabs Z3 bind command."""
    cli = f"zdo bind {nwk} {ep} 1 {cluster_id} {{{src}}} {{{dst}}}"
    return [{"commandcli": cli}]


# zdo unbind unicast [target:2] [source eui64:8] [source endpoint:1] [clusterID:2] [destinationEUI64:8] [destEndpoint:1]
def zdo_unbind(nwk: str, ep: int, cluster_id: int, src: str, dst: str) -> list:
    """Generate Silabs Z3 bind command."""
    cli = f"zdo unbind unicast {nwk} {{{src}}} {ep} {cluster_id} {{{dst}}} 1"
    return [{"commandcli": cli}]


# zcl global send-me-a-report [cluster:2] [attributeId:2] [dataType:1] [minReportTime:2] [maxReportTime:2] [reportableChange:-1]
# minReportTime Minimum number of seconds between reports
# maxReportTime Maximum number of seconds between reports
# reportableChange Amount of change to trigger a report
def zdb_report(
    nwk: str,
    ep: int,
    cluster_id: int,
    attr_id: int,
    mint: int,
    maxt: int,
    change: int,
    *,
    type_id: int = None,
):
    if type_id is None:
        type_id = get_type_id(cluster_id, attr_id)

    data = attr_encode(type_id, change).hex()
    cli = f"zcl global send-me-a-report {cluster_id} {attr_id} {type_id} {mint} {maxt} {{{data}}}"
    return [{"commandcli": cli}, {"commandcli": f"send {nwk} 1 {ep}"}]


# zdo leave [target:2] [removeChildren:1] [rejoin:1]
def zdo_leave(nwk: str):
    return [{"commandcli": f"zdo leave {nwk} 0 0"}]


# zdo mgmt-lqi [target:2] [startIndex:1]
def zdo_mgmt_lqi(nwk: str, index: int = 0):
    return [{"commandcli": f"zdo mgmt-lqi {nwk} {index}"}]


# 	zdo route [target:2] [index:1]
def zdo_route(nwk: str, index: int = 0):
    return [{"commandcli": f"zdo route {nwk} {index}"}]
