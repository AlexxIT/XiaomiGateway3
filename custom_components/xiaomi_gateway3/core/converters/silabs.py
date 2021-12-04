import logging

from zigpy.types import EUI64
from zigpy.zcl import Cluster
from zigpy.zcl.foundation import Command, ZCLHeader, Attribute, \
    ReadAttributeRecord, DATA_TYPES
from zigpy.zdo import ZDO
from zigpy.zdo.types import ZDOCmd, SizePrefixedSimpleDescriptor, NodeDescriptor

_LOGGER = logging.getLogger(__name__)

CLUSTERS = {}


# noinspection PyTypeChecker
def decode(data: dict):
    """Decode Silabs Z3 GatewayHost MQTT message using zigpy library. Supports
    ZDO payload and ZCL payload.
    """
    try:
        if data["sourceEndpoint"] == "0x00":
            # decode ZDO
            if "zdo" not in CLUSTERS:
                zdo = CLUSTERS["zdo"] = ZDO(None)
            else:
                zdo = CLUSTERS["zdo"]

            cluster_id = int(data['clusterId'], 0)
            raw = bytes.fromhex(data['APSPlayload'][2:])
            hdr, args = zdo.deserialize(cluster_id, raw)
            if hdr.command_id == ZDOCmd.Active_EP_rsp:
                return {
                    "command": str(hdr.command_id),
                    "status": str(args[0]),
                    "endpoints": args[2]
                }
            elif hdr.command_id == ZDOCmd.Simple_Desc_rsp:
                desc: SizePrefixedSimpleDescriptor = args[2]
                return {
                    "command": str(hdr.command_id),
                    "status": str(args[0]),
                    "device_type": desc.device_type,
                    "device_version": desc.device_version,
                    "endpoint": desc.endpoint,
                    "input_clusters": desc.input_clusters,
                    "output_clusters": desc.output_clusters,
                    "profile": desc.profile
                }
            elif hdr.command_id == ZDOCmd.Node_Desc_rsp:
                desc: NodeDescriptor = args[2]
                return {
                    "command": str(hdr.command_id),
                    "status": str(args[0]),
                    "is_mains_powered": desc.is_mains_powered,
                    "logical_type": str(desc.logical_type),
                    "manufacturer_code": desc.manufacturer_code,
                }
            elif hdr.command_id in (ZDOCmd.Bind_rsp, ZDOCmd.Mgmt_Leave_rsp):
                return {
                    "command": str(hdr.command_id),
                    "status": str(args[0]),
                }
            elif hdr.command_id in (ZDOCmd.Node_Desc_req, ZDOCmd.Active_EP_req):
                return {"command": str(hdr.command_id)}
            elif hdr.command_id == ZDOCmd.Simple_Desc_req:
                return {
                    "command": str(hdr.command_id),
                    "endpoint": args[0],
                }
            elif hdr.command_id == ZDOCmd.Bind_req:
                return {
                    "command": str(hdr.command_id),
                    "src_addr": args[0],
                    "src_endpoint": args[1],
                    "cluster": args[2],
                    "dst_addr": args[3]
                }
            elif hdr.command_id == ZDOCmd.IEEE_addr_rsp:
                return {
                    "command": str(hdr.command_id),
                    "status": args[0],
                    "ieee": args[1],
                    "nwk": args[2],
                }
            elif hdr.command_id == ZDOCmd.Mgmt_Leave_req:
                return {
                    "command": str(hdr.command_id),
                    "ieee": args[0],
                }
            elif hdr.command_id == ZDOCmd.Mgmt_NWK_Update_rsp:
                return {
                    "command": str(hdr.command_id),
                    "status": args[0],
                    "channels": args[1],
                    "total": args[2],
                    "failures": args[3],
                    "energy": args[4],
                }
            else:
                raise NotImplemented

        # decode ZCL
        cluster_id = int(data['clusterId'], 0)
        if cluster_id not in CLUSTERS:
            cluster = CLUSTERS[cluster_id] = Cluster.from_id(None, cluster_id)
            cluster._log = lambda *_, **__: None
        else:
            cluster = CLUSTERS[cluster_id]

        raw = bytes.fromhex(data['APSPlayload'][2:])
        try:
            hdr, args = cluster.deserialize(raw)
            hdr: ZCLHeader
        except ValueError as e:
            return {"cluster_id": cluster_id, "error": str(e)}
        except KeyError as e:
            return {"cluster_id": cluster_id, "error": f"Key error: {e}"}

        payload = {"endpoint": int(data["sourceEndpoint"], 0)}

        if cluster.ep_attribute:
            payload["cluster"] = cluster.ep_attribute
        else:
            payload["cluster_id"] = cluster_id

        if hdr.frame_control.is_general:
            payload["command"] = str(hdr.command_id)

            if (hdr.command_id == Command.Report_Attributes or
                    hdr.command_id == Command.Write_Attributes):
                attrs, = args
                for attr in attrs:
                    assert isinstance(attr, Attribute)
                    if attr.attrid in cluster.attributes:
                        name = cluster.attributes[attr.attrid][0]
                    else:
                        name = attr.attrid

                    value = attr.value.value
                    if isinstance(value, bytes) and value:
                        payload[name] = "0x" + value.hex()
                    elif isinstance(value, list) and \
                            not isinstance(value, EUI64):
                        payload[name] = [v.value for v in value]
                    else:
                        payload[name] = value

            elif hdr.command_id == Command.Read_Attributes_rsp:
                attrs, = args
                for attr in attrs:
                    assert isinstance(attr, ReadAttributeRecord)
                    if attr.attrid in cluster.attributes:
                        name = cluster.attributes[attr.attrid][0]
                    else:
                        name = attr.attrid

                    if attr.value is not None:
                        value = attr.value.value
                        if isinstance(value, bytes) and value:
                            payload[name] = "0x" + value.hex()
                        elif isinstance(value, list):
                            payload[name] = [v.value for v in value]
                        else:
                            payload[name] = value
                    else:
                        payload[name] = str(attr.status)

            elif hdr.command_id == Command.Read_Attributes:
                attrs, = args
                payload["value"] = attrs

            elif hdr.command_id == Command.Configure_Reporting:
                attrs, = args
                # fix __repr__ bug
                for attr in attrs:
                    if not hasattr(attr, "reportable_change"):
                        attr.reportable_change = None
                payload["value"] = attrs

            elif (hdr.command_id == Command.Write_Attributes_rsp or
                  hdr.command_id == Command.Configure_Reporting_rsp):
                resp, = args
                payload["status"] = [str(attr.status) for attr in resp]

            elif hdr.command_id == Command.Discover_Commands_Received_rsp:
                payload["status"] = bool(args[0])
                payload["value"] = args[1]

            elif hdr.command_id == Command.Default_Response:
                payload["value"] = args[0]
                payload["status"] = str(args[1])

            else:
                if isinstance(args, bytes) and args:
                    args = "0x" + args.hex()
                payload["command_id"] = int(hdr.command_id)
                payload["value"] = args

        elif hdr.frame_control.is_cluster:
            if isinstance(args, bytes) and args:
                args = "0x" + args.hex()

            payload["command_id"] = hdr.command_id
            if hdr.command_id < len(cluster.commands):
                payload["command"] = cluster.commands[hdr.command_id]
            if args:
                payload["value"] = args

        else:
            if isinstance(args, bytes) and args:
                args = "0x" + args.hex()

            payload.update({"command_id": hdr.command_id, "value": args})

        return payload

    except Exception as e:
        _LOGGER.debug("Error while parsing zigbee", exc_info=e)
        return None


def get_cluster(cluster: str) -> Cluster:
    # noinspection PyProtectedMember
    return next(
        cls for cls in Cluster._registry.values() if
        cls.ep_attribute == cluster
    )


def get_attr(attributes: dict, attr) -> int:
    if isinstance(attr, int):
        return attr
    return next(k for k, v in attributes.items() if v[0] == attr)


def get_attr_type(attributes: dict, attr: str) -> (int, int):
    attr, attr_type = next(
        (k, v[1]) for k, v in attributes.items()
        if v[0] == attr
    )
    type = next(k for k, v in DATA_TYPES.items() if v[1] == attr_type)
    return attr, type


def zcl_on_off(nwk: str, ep: int, value: bool) -> list:
    """Generate Silabs Z3 command (cluster 6)."""
    value = "on" if value else "off"
    return [
        {"commandcli": f"zcl on-off {value}"},
        {"commandcli": f"send {nwk} 1 {ep}"}
    ]


# zcl level-control mv-to-level [level:1] [transitionTime:2] [optionMask:1] [optionOverride:1]
def zcl_level(nwk: str, ep: int, br: int, tr: float) -> list:
    """Generate Silabs Z3 command (cluster 8)."""
    tr = int(tr * 10.0)  # zcl format - tenths of a seconds
    return [
        {"commandcli": f"zcl level-control o-mv-to-level {br} {tr}"},
        {"commandcli": f"send {nwk} 1 {ep}"}
    ]


def zcl_color(nwk: str, ep: int, ct: int, tr: float) -> list:
    """Generate Silabs Z3 command (cluster 0x0300)."""
    tr = int(tr * 10.0)  # zcl format - tenths of a seconds
    return [
        {"commandcli": f"zcl color-control movetocolortemp {ct} {tr} 0 0"},
        {"commandcli": f"send {nwk} 1 {ep}"}
    ]


# zcl global read [cluster:2] [attributeId:2]
def zcl_read(nwk: str, ep: int, cluster: str, *attrs) -> list:
    """Generate Silabs Z3 read attribute command. Support multiple attrs."""
    # convert string to object
    cluster = get_cluster(cluster)
    cid = cluster.cluster_id

    # convert List[str] to List[int]
    attrs = [get_attr(cluster.attributes, attr) for attr in attrs]

    if len(attrs) > 1:
        raw = "".join([int(a).to_bytes(2, "little").hex() for a in attrs])
        return [
            {"commandcli": f"raw {cid} {{100000{raw}}}"},
            {"commandcli": f"send {nwk} 1 {ep}"},
        ]

    return [
        {"commandcli": f"zcl global read {cid} {attrs[0]}"},
        {"commandcli": f"send {nwk} 1 {ep}"}
    ]


# zcl global write [cluster:2] [attributeId:2] [type:4] [data:-1]
def zcl_write(
        nwk: str, ep: int, cluster: str, attr, data, mfg: int = None,
        type: int = None
) -> list:
    """Generate Silabs Z3 write attribute command."""
    cluster = get_cluster(cluster)
    cid = cluster.cluster_id

    if isinstance(attr, str):
        attr, type = get_attr_type(cluster.attributes, attr)

    # TODO: other types...
    if type in (0x10, 0x30):
        data = f"{{{data:02x}}}"
    elif type == 33:
        data = "{" + int(data).to_bytes(2, "little").hex() + "}"

    pre = [
        {"commandcli": f"zcl mfg-code {mfg}"}
    ] if mfg is not None else []
    return pre + [
        {"commandcli": f"zcl global write {cid} {attr} {type} {data}"},
        {"commandcli": f"send {nwk} 1 {ep}"}
    ]


def zdo_bind(nwk: str, ep: int, cluster: str, src: str, dst: str) -> list:
    """Generate Silabs Z3 bind command."""
    cluster = get_cluster(cluster)
    cid = cluster.cluster_id
    return [{
        "commandcli": f"zdo bind {nwk} {ep} 1 {cid} {{{src}}} {{{dst}}}"
    }]


# zcl global send-me-a-report [cluster:2] [attributeId:2] [dataType:1] [minReportTime:2] [maxReportTime:2] [reportableChange:-1]
def zdb_report(
        nwk: str, ep: int, cluster: str, attr: str, mint: int, maxt: int,
        change: int, type: int = None
):
    cluster = get_cluster(cluster)
    cid = cluster.cluster_id

    if isinstance(attr, str):
        attr, type = get_attr_type(cluster.attributes, attr)

    change = int(change).to_bytes(2, "little").hex()
    return [{
        "commandcli": f"zcl global send-me-a-report {cid} {attr} {type} {mint} {maxt} {{{change}}}"
    }, {
        "commandcli": f"send {nwk} 1 {ep}"
    }]
